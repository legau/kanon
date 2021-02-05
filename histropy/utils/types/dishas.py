from typing import Any, Dict, List, Literal, Optional, TypedDict

# flake8: noqa


class OriginalValue(TypedDict):
    value: List[str]
    comment: str
    suggested: bool
    critical_apparatus: List[str]


NumberType = Literal["sexagesimal", "floating sexagesimal", "integer and sexagesimal"]
SymmetryType = Literal["mirror", "periodic"]
SymmetryOperation = Literal["opposite", "identity", "addition", "substraction"]
UnitType = Literal["degree", "day"]


class Template(TypedDict):

    table_type: str
    readonly: bool
    args: List[TypedDict("args", {
        "name": str,
        "type": NumberType,
        "unit": int,
        "nsteps": int,
        "ncells": int,
        "decpos": int,
        "subUnit": Optional[NumberType],
        "firstMonth": Optional[Any]
    })]
    entries: List[TypedDict("entries", {
        "name": str,
        "type": NumberType,
        "ncells": int,
        "decpos": int,
        "unit": int
    })]


class DSymmetry(TypedDict):
    type: SymmetryType
    parameter: str
    sign: Literal[-1, 1]
    displacement: str
    source: List[str]
    target: List[str]
    direction: Literal[-1, 1]
    effective_symmetry: TypedDict("effective_symmetry", {
        "computeNewValue": List[SymmetryOperation],
        "parameters": List[str]
    })


class TableContent(TypedDict):
    argument1_number_of_steps: int
    argument2_number_of_steps: Optional[int]
    id: int
    value_original: TypedDict("value_original", {
        "args": TypedDict("args", {
            "argument1": List[OriginalValue],
            "argument2": Optional[List[OriginalValue]]
        }),
        "entry": List[OriginalValue],
        "template": Template,
        "symmetries": List[DSymmetry]
    })
    value_float: TypedDict("value_float", {
        "args": TypedDict("args", {
            "argument1": List[str],
            "argument2": Optional[List[str]]
        }),
        "entry": List[str],
        "template": Template
    })
    corrected_value_float: TypedDict("value_corrected", {
        "args": TypedDict("args", {
            "argument1": List[str],
            "argument2": Optional[List[str]]
        }),
        "entry": List[str],
        "template": Template
    })
    edited_text: Dict
    entry_type_of_number: NumberType
    entry_number_unit: UnitType
    entry_significant_fractional_place: str
    entry_number_of_cell: str
    argument1_name: str
    argument1_type_of_number: NumberType
    argument1_number_unit: UnitType
    argument1_number_of_cell: str
    argument1_significant_fractional_place: str
    argument2_name: Optional[str]
    argument2_type_of_number: NumberType
    argument2_number_unit: Optional[UnitType]
    argument2_number_of_cell: Optional[str]
    argument2_significant_fractional_place: Optional[str]
    comment: str
    mathematical_parameter: str
    parameter_sets: Dict
    table_type: Dict
    created: str
    updated: str
    public: Literal[True]
    mean_motion: Optional[Any]
    kibana_name: str
    kibana_id: str
