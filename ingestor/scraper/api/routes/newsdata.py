from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
from ..utils import JsonApiTemplate

router = APIRouter(
    prefix="/api",
    tags=["news"]
)

ApiResponse = JsonApiTemplate("api")

@router.get("/news")
async def get_news():
    """Get crypto news from news.json file"""
    try:
        # Path to the news.json file in the data folder
        news_file_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "news.json"
        
        if not news_file_path.exists():
            myResponse = ApiResponse._create_response(
                level="error",
                msg="News file not found",
                response={
                    "status": 404,
                    "error": "News file not found"
                }
            )
            raise HTTPException(status_code=404, detail=myResponse)
        
        # Read the news file
        with open(news_file_path, 'r', encoding='utf-8') as file:
            news_data = json.load(file)
        
        # Filter articles with content
        articles_with_content = [article for article in news_data if article.get('has_content', False)]
        
        myResponse = ApiResponse._create_response(
            level="info",
            msg="News data retrieved successfully",
            response={
                "status": 200,
                "data": articles_with_content,
                "count": len(articles_with_content)
            }
        )
        
        return myResponse
        
    except FileNotFoundError:
        myResponse = ApiResponse._create_response(
            level="error",
            msg="News file not found",
            response={
                "status": 404,
                "error": "News file not found"
            }
        )
        raise HTTPException(status_code=404, detail=myResponse)
    except json.JSONDecodeError:
        myResponse = ApiResponse._create_response(
            level="error",
            msg="Invalid JSON format in news file",
            response={
                "status": 500,
                "error": "Invalid JSON format in news file"
            }
        )
        raise HTTPException(status_code=500, detail=myResponse)
    except Exception as e:
        myResponse = ApiResponse._create_response(
            level="error",
            msg="Error reading news",
            response={
                "status": 500,
                "error": f"Error reading news: {str(e)}"
            }
        )
        raise HTTPException(status_code=500, detail=myResponse)