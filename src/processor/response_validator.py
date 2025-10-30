import json
import pandas as pd
from typing import Dict, Any
from tabulate import tabulate
from difflib import SequenceMatcher
from sklearn.metrics import confusion_matrix


def sequence_matcher_similarity(element1, element2):
    if type(element1) != type(element2):
        return 0
    if isinstance(element1, bool):
        return int(element1 == element2)
    return SequenceMatcher(None, element1, element2).ratio()


def sequence_matcher_lst_similarity(lst1: list, lst2: list):
    score_lst = []
    len1, len2 = len(lst1), len(lst2)

    if len1 == len2:
        score_lst = [sequence_matcher_similarity(
            e1, e2) for e1, e2 in zip(lst1, lst2)]
        return sum(score_lst) / len1

    num_min_elements = min(len1, len2)
    score_lst = [
        2 * sequence_matcher_similarity(lst1[i], lst2[i]) for i in range(num_min_elements)]

    return sum(score_lst) / (2 * num_min_elements + abs(len1 - len2))


class EntityExtractionValidator:
    def __init__(
            self,
            validation_file: str,
            schema_file: str,
    ):
        self.validation_file = validation_file
        self.schema_file = schema_file

    def validate_document(self, pred: Dict[str, Any], multimodal_eval: bool = False, verbose: bool = False) -> None:

        track_result = {}

        flag = True  # Flag to indicate if validation is successful
        try:
            with open(self.schema_file, 'r') as file:
                schema = json.load(file)
            with open(self.validation_file, 'r') as file:
                gt = json.load(file)

            if not all(key in schema for key in ['steps']) or not all(key in gt for key in ['steps']) or 'steps' not in pred:
                raise ValueError("Missing `steps` key in one of the files.")
        except Exception as e:
            raise ValueError(f"Error loading schema or validation file: {e}")

        # Compare each step
        for index, _step in enumerate(schema['steps']):
            step_name = _step['step']
            try:
                fields_gt_lst = next(
                    (step['fields'] for step in gt['steps'] if step['step'] == step_name), None)
                fields_pred_lst = next(
                    (step['fields'] for step in pred['steps'] if step['step'] == step_name), None)
                if fields_pred_lst is None:
                    print(f"No matching step found for step name: {step_name}")
                    flag = False
                    break
            except Exception as e:
                print(f"Error: {e}")
                flag = False
                break

            for field_gt in fields_gt_lst:
                field_name_gt = field_gt.get('name')
                field_value_gt = field_gt.get('value')
                field_type_gt = field_gt.get('type')
                field_pred = next((field for field in fields_pred_lst if field['name'].lower(
                ) == field_name_gt.lower()), None)

                # Skip if field not found in prediction
                if field_pred is None:
                    track_result[field_type_gt]['error'].append({
                        'step': _step['step'],
                        'field_name': field_name_gt,
                        'error': f'Field `{field_name_gt}` not found in prediction'
                    })
                    continue

                if field_type_gt not in track_result:
                    track_result[field_type_gt] = {
                        'gt_value': [],
                        'pred_value': [],
                        'similar_score': [],
                        'total': 0,
                        'correct': 0,
                        'error': [],
                    }
                    if field_type_gt == 'string':
                        track_result[field_type_gt]['similar_lowercase_score'] = []
                else:
                    pass

                field_type_pred = field_pred.get('type')
                field_values_pred = field_pred.get('values')
                if multimodal_eval:
                    field_multimodal_value_pred = [_value.get(
                        'multimodal_value') for _value in field_values_pred]
                    if field_type_gt in ['string', 'boolean']:
                        field_value_pred = field_multimodal_value_pred[0]
                    else:  # list[string] or list[boolean]
                        field_value_pred = field_multimodal_value_pred
                else:
                    field_value_pred = [_value['value']
                                        for _value in field_values_pred]
                    if field_type_gt in ['string', 'boolean']:
                        field_value_pred = field_value_pred[0]

                try:
                    if field_type_gt == 'string':
                        similar_score = sequence_matcher_similarity(
                            field_value_gt, field_value_pred)
                        similar_lower_score = sequence_matcher_similarity(
                            field_value_gt.lower(), field_value_pred.lower())
                    elif field_type_gt == 'boolean':
                        similar_score = sequence_matcher_similarity(
                            field_value_gt, field_value_pred)
                        similar_lower_score = None
                    else:  # handle list[string] and list[boolean]
                        similar_score = sequence_matcher_lst_similarity(
                            field_value_gt, field_value_pred)
                        similar_lower_score = None
                except Exception as e:
                    print(f"Error calculating similarity: {e}")
                    print(f"Field Name: {field_name_gt}")
                    print(f"Field Value GT: {field_value_gt}")
                    print(f"Field Value Pred: {field_value_pred}")

                    similar_score = 0.0
                    similar_lower_score = 0.0 if field_type_gt == 'string' else None

                track_result[field_type_gt]['gt_value'].append(field_value_gt)
                track_result[field_type_gt]['pred_value'].append(
                    field_value_pred)
                track_result[field_type_gt]['similar_score'].append(
                    similar_score)
                if similar_lower_score is not None:
                    track_result[field_type_gt]['similar_lowercase_score'].append(
                        similar_lower_score)
                track_result[field_type_gt]['total'] += 1
                track_result[field_type_gt]['correct'] += (
                    similar_score == 1.0)
                if similar_score < 1.0:
                    error_entry = {
                        'step': _step['step'],
                        'field_name': field_name_gt,
                        'field_value_gt': field_value_gt,
                        'field_value_pred': field_value_pred,
                        'similar_score': similar_score
                    }
                    if similar_lower_score is not None:
                        error_entry['similar_lower_score'] = similar_lower_score
                    track_result[field_type_gt]['error'].append(error_entry)

        # with open(r"C:\Projects\mee-landingai\track_results.json", 'w') as file:
        #     json.dump(track_result, file, indent=4)

        if verbose and flag:
            self._validate_verbose(track_result)

    @staticmethod
    def _calculate_boolean_accuracy(gt: str, pred: str) -> float:
        '''
        Returns the F1 score for boolean values. If groundtruth does not contain positive value, specificity  is returned instead.
        '''

        # Calculate confusion matrix
        tn, fp, fn, tp = confusion_matrix(
            gt, pred, labels=[False, True]).ravel()
        if tp == 0:
            return tn / (tn + fp)
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        return 2 * (precision * recall) / (precision + recall)

    def _validate_verbose(self, track_result: Dict[str, Any]) -> None:
        df = pd.DataFrame(columns=[
                          'Field Type', 'Total Field', 'Correct Field', 'Accuracy', 'Lowercase Accuracy'])
        for key, value in track_result.items():
            if value.get('similar_score'):
                accuracy = sum(value['similar_score']) / \
                    len(value['similar_score'])
                track_result[key]['accuracy'] = accuracy
                del track_result[key]['similar_score']
            else:
                accuracy = None

            if value.get('similar_lowercase_score'):
                accuracy_lowercase = sum(
                    value['similar_lowercase_score']) / len(value['similar_lowercase_score'])
                track_result[key]['accuracy_lowercase'] = accuracy_lowercase
                del track_result[key]['similar_lowercase_score']
            else:
                accuracy_lowercase = None

            if key == 'boolean':
                for i in range(len(value['pred_value'])):
                    if not isinstance(value['pred_value'][i], bool):
                        # Convert to boolean value. If not boolean, then it is incorrect, so set to False
                        value['pred_value'][i] = not value['gt_value'][i]
                accuracy = self._calculate_boolean_accuracy(
                    value['gt_value'], value['pred_value'])
                track_result[key]['accuracy'] = accuracy

            del track_result[key]['gt_value']
            del track_result[key]['pred_value']

            new_row = {
                'Field Type': key,
                'Total Field': value['total'],
                'Correct Field': value['correct'],
                'Accuracy': accuracy,
                'Lowercase Accuracy': accuracy_lowercase,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            print(f"Accuracy for `{key}` is {accuracy}")

        print(tabulate(df, headers='keys', tablefmt='simple'))
