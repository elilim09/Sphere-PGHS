from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(
    prefix="/lost",
    tags=["Lost & Found"]
)

#  데이터 모델
class LostItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    location: str
    contact: str

#  임시 DB (실제 운영시 DB로 교체)
lost_items: List[LostItem] = []


# 물건 등록
@router.post("/", response_model=LostItem)
def register_lost_item(item: LostItem):
    for i in lost_items:
        if i.id == item.id:
            raise HTTPException(status_code=400, detail="이미 존재하는 ID입니다.")
    lost_items.append(item)
    return item


#  물건 전체 조회
@router.get("/", response_model=List[LostItem])
def get_all_items():
    return lost_items


# 특정 물건 조회
@router.get("/{item_id}", response_model=LostItem)
def get_item(item_id: int):
    for item in lost_items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="물건을 찾을 수 없습니다.")


# 물건 삭제
@router.delete("/{item_id}")
def delete_item(item_id: int):
    global lost_items
    lost_items = [item for item in lost_items if item.id != item_id]
    return {"message": f"ID {item_id} 물건이 삭제되었습니다."}
