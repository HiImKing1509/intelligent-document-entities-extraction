import re
import json
from abc import ABC, abstractmethod
from loguru import logger

from typing import Dict, Any, List, Type, Tuple, Union, Optional
from pydantic import BaseModel, Field, create_model, ConfigDict, ValidationError


class JSON2PydanticConverter(ABC):
    """
    Converts a JSON schema dictionary into a Pydantic model, primarily for use
    with OpenAI's structured outputs.
    """

    # Counter to ensure unique names for dynamically generated nested Pydantic models.
    _nested_model_counter: int = 0

    @staticmethod
    def _sanitize_model_name(name: str) -> str:
        """
        Sanitizes a string to be a valid Python identifier for model names.
        - Removes characters invalid for Python identifiers, replaces with '_'.
        - Handles names starting with a digit by prepending 'Model_'.
        - Collapses multiple underscores and strips leading/trailing ones.
        """
        if not isinstance(name, str):
            name = str(name)  # Attempt to convert to string if not already

        # Remove characters invalid for Python identifiers, replace with '_'
        name = re.sub(r"\W|^(?=\d)", "_", name)

        # Replace multiple consecutive underscores with a single one
        name = re.sub(r"_+", "_", name)

        # Remove leading/trailing underscores
        name = name.strip("_")

        # Ensure the name is not empty and starts with a letter or underscore
        if not name or (not name[0].isalpha() and name[0] != "_"):
            # Ensures it starts with a letter or underscore.
            name = f"Model_{name}"

        return name if name else "DefaultGeneratedModel"

    def _generate_unique_nested_model_name(self, model_name_prefix: str, original_key: str) -> str:
        """
        Generates a unique and valid Python class name for a nested Pydantic model.
        Example: If parent is 'Root' and key is 'User Details', could be 'Root_UserDetails_M1'.
        """
        JSON2PydanticConverter._nested_model_counter += 1
        sanitized_key_part = self._sanitize_model_name(original_key)

        # Ensure sanitized_key_part is not empty and provides a good naming component.
        if not sanitized_key_part:
            sanitized_key_part = "Nested"

        return f"{model_name_prefix}_{sanitized_key_part}_M{JSON2PydanticConverter._nested_model_counter}"

    @abstractmethod
    def _convert_dict_to_model(self):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def convert(self):
        raise NotImplementedError("Subclasses must implement this method.")

    @staticmethod
    def print_pydantic_model_schema(model_class: Type[BaseModel], _indent_level: int = 0) -> None:
        """
        Prints the schema details of a Pydantic model, including nested models.

        Args:
            model_class: The Pydantic model class.
            _indent_level: Current indentation level (for recursive calls).
        """
        base_indent = "  " * _indent_level
        if not hasattr(model_class, 'model_fields'):
            print(
                f"{base_indent}Error: {model_class} is not a Pydantic model or has no fields.")
            return

        for field_name, field_info in model_class.model_fields.items():
            alias = field_info.alias if field_info.alias else field_name
            description = field_info.description if field_info.description else ""
            print(f"{base_indent}  - Pydantic Name: {field_name}, Type: {field_info.annotation}, Alias: '{alias}', Description: '{description}'")

            annotation_to_check = []
            if hasattr(field_info.annotation, 'model_fields') and issubclass(field_info.annotation, BaseModel):
                annotation_to_check.append(field_info.annotation)
            else:
                from typing import get_origin, get_args
                origin = get_origin(field_info.annotation)
                if origin in (List, Union, Optional) or str(origin) in ("typing.List", "typing.Union", "typing.Optional"):
                    args = get_args(field_info.annotation)
                    for arg in args:
                        if hasattr(arg, 'model_fields') and isinstance(arg, type) and issubclass(arg, BaseModel):
                            annotation_to_check.append(arg)

            for nested_model_class in annotation_to_check:
                print(
                    f"{base_indent}    Nested Model '{nested_model_class.__name__}' Fields (for field '{field_name}'):")
                JSON2PydanticConverter.print_pydantic_model_schema(
                    nested_model_class, _indent_level + 2)

    def serialize(self, model_class: Type[BaseModel], data: Any, verbose=False) -> Dict[str, Any]:
        """
        Attempts to instantiate a Pydantic model with the given data dictionary
        and prints its JSON representation or validation errors.

        Args:
            model_class: The Pydantic model class.
            data_dict: The dictionary to instantiate the model with (using aliases).
        """
        if not isinstance(data, model_class):
            logger.error(
                f"Data is not an instance of {model_class.__name__}. Cannot serialize.")
            return {}

        data_dict = data.model_dump(by_alias=True)

        if verbose:
            print(
                f"\n--- Attempting instantiation for {model_class.__name__} ---")
            try:
                instance = model_class(**data_dict)

                print("Instantiation successful!")
                print("Instantiated Model (JSON by alias):")
                print(instance.model_dump_json(by_alias=True, indent=2))

                # Also print the Pydantic schema for OpenAI (as in the original example)
                # Ensure by_alias=True is used if your OpenAI functions expect original JSON keys
                print(
                    f"Pydantic schema for OpenAI (by alias): {model_class.model_json_schema(by_alias=True)}")

            except ValidationError as e:
                print(
                    f"Validation Error during instantiation of {model_class.__name__}: {e}")
            except Exception as e:
                print(
                    f"An unexpected error occurred during instantiation of {model_class.__name__}: {e}")

        return data_dict


class StructuredJSON2PydanticConverter(JSON2PydanticConverter):

    def _convert_dict_to_model(
        self,
        schema_dict: Dict[str, Any],
        model_py_name: str,
    ) -> Type[BaseModel]:
        """
        Recursively creates a Pydantic model from a dictionary schema.

        Args:
            schema_dict: The dictionary defining the schema for the current model.
            model_py_name: The Python-valid class name for the Pydantic model to be created.
            current_model_name_prefix_for_children: A prefix used for generating names of any nested models.

        Returns:
            The dynamically created Pydantic model class.
        """
        if not isinstance(schema_dict, dict):
            raise TypeError(
                f"Input schema for model '{model_py_name}' must be a dictionary. "
                f"Received: {type(schema_dict)}"
            )

        field_definitions: Dict[str, Tuple[Any, Any]] = {}
        # Field counter for generating Pydantic field names like field_1, field_2, ...
        # This counter is local to each model being defined.
        pydantic_field_index = 1

        # Base class for all dynamically created models, enforcing strictness and alias usage.
        class DynamicModelBase(BaseModel):
            model_config = ConfigDict(
                extra='forbid',
                populate_by_name=True,
                validate_assignment=True
            )

        for original_key, value_schema in schema_dict.items():
            # pydantic_internal_field_name = f"field_{pydantic_field_index}"
            pydantic_internal_field_name = self._sanitize_model_name(
                original_key)
            pydantic_field_index += 1

            current_field_type: Any

            if isinstance(value_schema, dict):
                nested_model_py_name = self._generate_unique_nested_model_name(
                    model_py_name, original_key
                )
                current_field_type = self._convert_dict_to_model(
                    value_schema,
                    nested_model_py_name
                )
            elif isinstance(value_schema, list):
                if not value_schema:
                    element_type = str
                elif len(value_schema) == 1 and value_schema[0] == "":
                    element_type = str
                elif len(value_schema) == 1 and value_schema[0] == "bool":
                    element_type = bool
                else:
                    raise ValueError(
                        f"Unsupported list schema for key '{original_key}': {value_schema}. "
                        f"Expected an empty list [], or a list with a single type indicator like [''] or ['bool']."
                    )
                current_field_type = List[element_type]
            elif value_schema == "bool":
                current_field_type = bool
            elif value_schema == "":
                current_field_type = str
            else:
                raise ValueError(
                    f"Unsupported schema value for key '{original_key}': {value_schema}. "
                    f"Expected a dictionary (for nested model), list (e.g., [], [''], or ['bool']), "
                    f"the string 'bool' (for boolean), or an empty string '' (for string)."
                )

            field_definitions[pydantic_internal_field_name] = (
                current_field_type, Field(...,
                                          description=original_key, alias=original_key)
            )

        try:
            CreatedModel: Type[BaseModel] = create_model(
                model_py_name,
                **field_definitions,
                __base__=DynamicModelBase
            )
            return CreatedModel
        except Exception as e:
            raise RuntimeError(
                f"Pydantic 'create_model' failed for model '{model_py_name}': {e}"
            ) from e

    def convert(self, json_input_schema: Dict[str, Any], root_model_name: str = "RootModel") -> Type[BaseModel]:

        if not isinstance(json_input_schema, dict):
            raise TypeError("Input JSON schema must be a dictionary.")

        JSON2PydanticConverter._nested_model_counter = 0

        root_model_class = self._convert_dict_to_model(
            schema_dict=json_input_schema,
            model_py_name=root_model_name,
        )
        return root_model_class
