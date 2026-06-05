"""
labelling.py

A small vanilla-Python module for labelling product of the order data (tuples) using a SKU label CSV.

The CSV is expected to contain an ID column and these 6 label columns:
    Category, Sub-category, Product Name, Product Variant, Brand, Pack Size

Example:
    from product_sku_labeler import label_tuples_from_csv

    orders_data = [
        ("1732880134400804143", "some existing value"),
        ("1732880134400869679", "another existing value"),
    ]

    labelled_tuples, missing_ids = label_tuples_from_csv(
        csv_path="Product_SKU_Label.csv",
        tuples=orders_data,
        id_index=0,
    )

    print(labelled_tuples)
    print(missing_ids)
"""

from __future__ import annotations

import csv
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union


DEFAULT_ID_COLUMN = "ID"

DEFAULT_LABEL_COLUMNS = (
    "Category",
    "Sub-category",
    "Product SKU Name",
    "Product Variant",
    "Brand",
    "Pack Size",
)

LabelTuple = Tuple[Optional[str], ...]
InputTuple = Tuple[object, ...]
LabelLookup = Dict[str, LabelTuple]


def _clean_value(value: object) -> Optional[str]:
    """Convert a CSV value to a clean string, preserving empty values as empty strings."""
    if value is None:
        return None
    return str(value).strip()


def load_label_lookup(
    csv_path: str,
    id_column: str = DEFAULT_ID_COLUMN,
    label_columns: Sequence[str] = DEFAULT_LABEL_COLUMNS,
    encoding: str = "utf-8-sig",
) -> LabelLookup:
    """
    Load the label CSV into a dictionary keyed by product ID.

    Args:
        csv_path: Path to the labelling CSV file.
        id_column: Name of the ID column in the CSV.
        label_columns: Label columns to append to each tuple.
        encoding: File encoding. utf-8-sig handles CSV files with BOM.

    Returns:
        A dictionary like:
        {
            "product_id": (
                Category,
                Sub-category,
                Product SKU Name,
                Product Variant,
                Brand,
                Pack Size,
            )
        }

    Raises:
        ValueError: If required columns are missing.
    """
    lookup: LabelLookup = {}

    with open(csv_path, mode="r", encoding=encoding, newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or has no header row.")

        missing_columns = [
            column
            for column in (id_column, *label_columns)
            if column not in reader.fieldnames
        ]

        if missing_columns:
            raise ValueError(
                "CSV file is missing required column(s): "
                + ", ".join(missing_columns)
            )

        for row in reader:
            product_id = _clean_value(row.get(id_column))

            # Skip rows with empty IDs.
            if not product_id:
                continue

            lookup[product_id] = tuple(
                _clean_value(row.get(column))
                for column in label_columns
            )

    return lookup


def label_tuples(
    tuples: Iterable[InputTuple],
    label_lookup: LabelLookup,
    id_index: int = 0,
    missing_value: Optional[str] = None,
    return_missing_ids: bool = True,
) -> Union[List[InputTuple], Tuple[List[InputTuple], List[str]]]:
    """
    Append labels to each tuple by matching the tuple's ID to the label lookup.

    Args:
        tuples: Iterable of tuples to label.
        label_lookup: Dictionary created by load_label_lookup().
        id_index: The position of the product ID inside each tuple.
        missing_value: Value used for each label when an ID is not found.
        return_missing_ids: If True, return (labelled_tuples, missing_ids).
            If False, return only labelled_tuples.

    Returns:
        Either:
            labelled_tuples
        or:
            (labelled_tuples, missing_ids)

    Example output tuple:
        (
            original_id,
            original_value_1,
            Category,
            Sub-category,
            Product Name,
            Product Variant,
            Brand,
            Pack Size,
        )
    """
    labelled_tuples: List[InputTuple] = []
    missing_ids: List[str] = []

    label_count = 0
    if label_lookup:
        first_labels = next(iter(label_lookup.values()))
        label_count = len(first_labels)

    for item in tuples:
        try:
            product_id = _clean_value(item[id_index])
        except IndexError as exc:
            raise IndexError(
                f"Tuple {item!r} does not have an element at id_index={id_index}."
            ) from exc

        labels = label_lookup.get(product_id or "")

        if labels is None:
            if product_id is not None:
                missing_ids.append(product_id)
            labels = tuple(missing_value for _ in range(label_count))

        labelled_tuples.append(item + labels)

    if return_missing_ids:
        return labelled_tuples, missing_ids

    return labelled_tuples


def label_tuples_from_csv(
    csv_path: str,
    tuples: Iterable[InputTuple],
    id_index: int = 0,
    id_column: str = DEFAULT_ID_COLUMN,
    label_columns: Sequence[str] = DEFAULT_LABEL_COLUMNS,
    missing_value: Optional[str] = None,
    encoding: str = "utf-8-sig",
) -> Tuple[List[InputTuple], List[str]]:
    """
    Convenience function: load the CSV and label tuples in one call.

    Returns:
        (labelled_tuples, missing_ids)
    """
    label_lookup = load_label_lookup(
        csv_path=csv_path,
        id_column=id_column,
        label_columns=label_columns,
        encoding=encoding,
    )

    return label_tuples(
        tuples=tuples,
        label_lookup=label_lookup,
        id_index=id_index,
        missing_value=missing_value,
        return_missing_ids=True,
    )


def write_labelled_tuples_to_csv(
    output_path: str,
    labelled_tuples: Iterable[InputTuple],
    headers: Optional[Sequence[str]] = None,
    encoding: str = "utf-8-sig",
) -> None:
    """
    Optional helper to export labelled tuples to a CSV file.

    Args:
        output_path: Where to save the output CSV.
        labelled_tuples: Tuples returned by label_tuples() or label_tuples_from_csv().
        headers: Optional CSV header row.
        encoding: Output encoding.
    """
    with open(output_path, mode="w", encoding=encoding, newline="") as file:
        writer = csv.writer(file)

        if headers:
            writer.writerow(headers)

        writer.writerows(labelled_tuples)

def add_label_header_tuple(headers):
    """
    Return a new header tuple with the 6 product label columns appended.

    Args:
        headers (tuple): Original header columns.

    Returns:
        tuple: Original headers + product label headers.
    """
    label_headers = (
        "Category",
        "Sub-category",
        "Product SKU Name",
        "Product Variant",
        "Brand",
        "Pack Size",
    )

    return tuple(headers) + label_headers


if __name__ == "__main__":
    # Example usage. Replace this list with your real tuple list.
    product_tuples = [
        ("1732880134400804143", "example_existing_value"),
        ("1732880134400869679", "example_existing_value"),
        ("missing_id_example", "example_existing_value"),
    ]

    labelled, missing = label_tuples_from_csv(
        csv_path="Product_SKU_Label.csv",
        tuples=product_tuples,
        id_index=0,
    )

    print("Labelled tuples:")
    for row in labelled:
        print(row)

    print("\nMissing IDs:", missing)