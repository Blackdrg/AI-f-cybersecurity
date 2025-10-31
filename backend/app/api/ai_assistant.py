from fastapi import APIRouter, HTTPException, Depends
from ..schemas import AIAssistantRequest, AIAssistantResponse
from ..security import get_current_user

try:
    from openai import OpenAI
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
    else:
        client = None
        OPENAI_AVAILABLE = False
except ImportError:
    OPENAI_AVAILABLE = False
    client = None

router = APIRouter()


@router.post("/ai/assistant", response_model=AIAssistantResponse)
async def ai_assistant_query(request: AIAssistantRequest, current_user=Depends(get_current_user)):
    """Query the AI assistant for help with face recognition tasks."""
    if not OPENAI_AVAILABLE:
        # Fallback response when OpenAI is not available
        return AIAssistantResponse(
            query=request.query,
            response="AI assistant is currently unavailable. Please check your OpenAI API key configuration.",
            model_used="fallback"
        )

    try:
        # Special case: Premium AI assistant for daredevil0101a@gmail.com
        if current_user.get("email") == "daredevil0101a@gmail.com":
            # Use GPT-4 with higher limits for premium user
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a premium AI assistant specialized in face recognition technology and computer vision. Provide expert-level assistance with advanced technical details, implementation guidance, and cutting-edge research insights."},
                    {"role": "user", "content": request.query}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content

            return AIAssistantResponse(
                query=request.query,
                response=ai_response,
                model_used="gpt-4"
            )

        # Create a system prompt for face recognition assistance
        system_prompt = """
        You are an AI assistant specialized in face recognition technology and computer vision.
        Help users with questions about face recognition, biometric authentication, and related technologies.
        Provide accurate, helpful information while maintaining privacy and ethical considerations.
        """

        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.query}
            ],
            max_tokens=500,
            temperature=0.7
        )

        ai_response = response.choices[0].message.content

        return AIAssistantResponse(
            query=request.query,
            response=ai_response,
            model_used="gpt-3.5-turbo"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"AI assistant error: {str(e)}")


@router.post("/ai/analyze-image")
async def analyze_image_with_ai(image_data: dict, current_user=Depends(get_current_user)):
    """Analyze an uploaded image using AI vision capabilities."""
    try:
        # This would integrate with OpenAI's vision API
        # For now, return a placeholder response
        return {
            "analysis": "Image analysis feature coming soon",
            "detected_features": ["face", "expression"],
            "confidence": 0.95
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Image analysis error: {str(e)}")
