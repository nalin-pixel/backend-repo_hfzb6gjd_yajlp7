import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Page

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# ---------- Builder Endpoints ----------

class SavePageRequest(BaseModel):
    title: str
    layout: Dict[str, Any] | List[Dict[str, Any]]
    status: Optional[str] = "draft"

@app.post("/api/pages")
def save_page(payload: SavePageRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    page = Page(title=payload.title, layout=payload.layout, status=payload.status)
    inserted_id = create_document("page", page)
    return {"id": inserted_id}

@app.get("/api/pages")
def list_pages(limit: int = 20):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("page", {}, limit)
    # Convert ObjectId and datetime to strings
    for d in docs:
        if isinstance(d.get("_id"), ObjectId):
            d["id"] = str(d.pop("_id"))
        # Convert any non-JSON types
        for k, v in list(d.items()):
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
    return {"items": docs}

@app.get("/api/pages/{page_id}")
def get_page(page_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson.objectid import ObjectId as _ObjectId
    try:
        oid = _ObjectId(page_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid page id")
    doc = db["page"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Page not found")
    doc["id"] = str(doc.pop("_id"))
    for k, v in list(doc.items()):
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc

@app.put("/api/pages/{page_id}")
def update_page(page_id: str, payload: SavePageRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson.objectid import ObjectId as _ObjectId
    try:
        oid = _ObjectId(page_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid page id")
    update_data = {
        "title": payload.title,
        "layout": payload.layout,
        "status": payload.status,
    }
    from datetime import datetime, timezone
    update_data["updated_at"] = datetime.now(timezone.utc)
    result = db["page"].update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"updated": True}

