import inspect
from abc import ABC, abstractmethod
from inspect import Parameter, Signature
from typing import Annotated, Any

from fastapi import Depends, Request
from pydantic import BaseModel


class ReplaceSignatureDependency(ABC):
    """The signature of the parameter in the endpoint of ORMAdapter.

    Will be replaced with the signature of the corresponding
    Pydantic model in CRUDGenerator.
    """

    override: type[BaseModel] = None

    def __init__(self, override: type[BaseModel]):
        assert isinstance(override, type), (
            f"Expected a BaseModel subclass but got "
            f"{type(override).__name__} instead"
        )
        assert issubclass(override, BaseModel), (
            f"Expected a BaseModel subclass but got "
            f"{type(override).__name__} instead"
        )
        self.override = override

    @abstractmethod
    def get_new_params(self, original: Parameter) -> list[Parameter]:
        pass

    def pack_to_originals(self, original_name: str, **kwargs):
        return kwargs

class ReplaceSingleSignatureDependency(ReplaceSignatureDependency):
    def get_new_params(self, original: Parameter) -> list[Parameter]:
        """Replace the annotation of the original parameter with the override.

        Args:
            original (Parameter): The original parameter whose annotation
                is to be replaced.

        Returns:
            list[Parameter]: A list containing a single parameter with
                the updated annotation.

        """
        return [inspect.Parameter(
                name=original.name,
                kind=original.kind,
                annotation=self.override,
        )]

class ReplaceWithAnnotationDependency(ReplaceSignatureDependency):
    """Replace a marker param with an arbitrary annotation."""

    def __init__(self, annotation: Any) -> None:
        self.annotation = annotation

    def get_new_params(self, original: Parameter) -> list[Parameter]:
        return [inspect.Parameter(
            name=original.name,
            kind=original.kind,
            annotation=self.annotation,
        )]


class ReplaceSubDependency(ReplaceSingleSignatureDependency):
    def get_new_params(self, original: Parameter) -> list[Parameter]:
        """Replace the original parameter with a Pydantic model sub-dependency.

        The new parameter injects a Pydantic model from query parameters;
        the model is defined in self.override.

        Args:
            original (Parameter): The original parameter of the endpoint.

        Returns:
            list[Parameter]: A list with one subdependency parameter.

        """
        new_params: list[inspect.Parameter]= [inspect.Parameter(
            name='request',
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Request,
        ) ]
        for field_name, field in self.override.model_fields.items():
            new_params.append(inspect.Parameter(
                name=field_name,
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=self.override.__annotations__[field_name],
                default=field.default,
            ))
        signature = Signature(new_params)

        def dependency(request: Request, **kwargs) -> self.override:
            # Distinguishing explicitly passed parameters from default values
            passed_param_names = set(request.query_params.keys())
            passed_params = {
                k: v for k, v in kwargs.items() if k in passed_param_names
            }
            return self.override(**passed_params)

        dependency.__signature__ = signature

        return [inspect.Parameter(
                name=original.name,
                kind=original.kind,
                annotation=Annotated[self.override, Depends(dependency)],
        )]

class ReplaceWithParamsListDependency(ReplaceSignatureDependency):
    """Explodes a Pydantic model into individual function parameters.

    Each model field becomes a separate parameter. If a field has a
    ``validation_alias``, that alias is used as the parameter name instead
    of the field name — useful for renaming path parameters (e.g. ``id``
    → ``user_id``) without changing the internal model field name.
    ``pack_to_originals`` reverses the mapping before calling the handler.
    """

    def get_new_params(self, original: Parameter) -> list[Parameter]:
        """Generate parameters from the fields of a Pydantic model.

        Replaces the original parameter with parameters derived from the fields
        of the model specified in self.override. Uses ``validation_alias`` as
        the parameter name when present.

        Args:
            original (Parameter): The original parameter to be replaced.

        Returns:
            list[Parameter]: A list of new parameters corresponding to the
                fields of the Pydantic model.

        """
        new_parameters = []
        for name, field_info in self.override.model_fields.items():
            param_name = field_info.validation_alias or name
            new_param = inspect.Parameter(
                name=param_name,
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=field_info.annotation,
            )
            new_parameters.append(new_param)
        return new_parameters

    def pack_to_originals(self, original_name: str, **kwargs):
        attr_values: dict = {}
        for name, field_info in self.override.model_fields.items():
            param_name = field_info.validation_alias or name
            attr_values[param_name] = kwargs.pop(param_name, None)
        value = self.override.model_validate(attr_values)
        kwargs[original_name] = value
        return kwargs


class CreateSchemaDependency(ReplaceSingleSignatureDependency):
    """Will be replaced with create_schema."""

class UpdateSchemaDependency(ReplaceSingleSignatureDependency):
    """Will be replaced with update_schema."""

class PublicSchemaDependency(ReplaceSingleSignatureDependency):
    """Will be replaced with public_schema."""

class PublicListSchemaDependency(ReplaceSingleSignatureDependency):
    """Will be replaced with public_list_schema."""

class FilterSchemaDependency(ReplaceSubDependency):
    """Will be replaced with filter_schema."""

class SortSchemaDependency(ReplaceSubDependency):
    """Will be replaced with sort_schema."""

class IncludeSchemaDependency(ReplaceSubDependency):
    """Will be replaced with include_schema."""

class PKFieldsDependency(ReplaceWithParamsListDependency):
    """Will be replaced with pk_fields."""

class ParentPKFieldsDependency(ReplaceWithParamsListDependency):
    """Will be replaced with parent collection's pk_fields in sub-collections."""

class PaginatorDependency(ReplaceWithAnnotationDependency):
    """Will be replaced with the ORM-specific paginator."""

    def __init__(self, paginator_class: type) -> None:
        super().__init__(
            Annotated[paginator_class, Depends(paginator_class)]
        )
