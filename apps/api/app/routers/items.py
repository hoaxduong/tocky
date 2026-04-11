from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.models.items import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])

# In-memory store for demonstration; replace with DB dependency later
_items: dict[int, ItemRead] = {}
_next_id: int = 1


@router.get("/")
def list_items(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ItemRead]:
    items = list(_items.values())
    return items[skip : skip + limit]


@router.post("/", status_code=201)
def create_item(item: ItemCreate) -> ItemRead:
    global _next_id
    new_item = ItemRead(id=_next_id, **item.model_dump())
    _items[_next_id] = new_item
    _next_id += 1
    return new_item


@router.get("/{item_id}")
def get_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
) -> ItemRead:
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    return _items[item_id]


@router.patch("/{item_id}")
def update_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    item_update: ItemUpdate,
) -> ItemRead:
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    existing = _items[item_id]
    update_data = item_update.model_dump(exclude_unset=True)
    updated = existing.model_copy(update=update_data)
    _items[item_id] = updated
    return updated


@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
) -> None:
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    del _items[item_id]
