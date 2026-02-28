from django.shortcuts import render
from django.conf import settings
from groq import Groq
import json

client = Groq(api_key=settings.GROQ_API_KEY)

def home(request):
    response_text = ""
    quiz_data = None
    quiz_results = None
    score = None
    flashcards = None
    user_input = ""

    # -----------------------------
    # QUIZ SUBMISSION (NO API CALL)
    # -----------------------------
    if request.method == "POST" and request.POST.get("submit_quiz"):
        quiz_json = request.POST.get("quiz_json", "")
        user_input = request.POST.get("user_input", "")

        # -----------------------------
        # Safely parse JSON
        # -----------------------------
        try:
            quiz_data = json.loads(quiz_json)  # Now this should work reliably
        except json.JSONDecodeError:
            return render(request, "index.html", {
                "response": "Quiz data corrupted. Please try again.",
                "user_input": user_input
            })

        score = 0
        quiz_results = []

        for i, q in enumerate(quiz_data):
            user_answer = request.POST.get(f"question_{i}")
            is_correct = (user_answer == q["answer"])
            if is_correct:
                score += 5
            quiz_results.append({
                "question": q["question"],
                "user_answer": user_answer,
                "correct_answer": q["answer"],
                "is_correct": is_correct
            })

        # Render results after quiz submission
        return render(request, "index.html", {
            "quiz": quiz_data,
            "quiz_results": quiz_results,
            "score": score,
            "user_input": user_input
        })

    # -----------------------------
    # NORMAL AI REQUEST
    # -----------------------------
    elif request.method == "POST":
        user_input = request.POST.get("user_input", "")
        action = request.POST.get("action", "")

        if not user_input:
            return render(request, "index.html", {"response": "Please enter a topic."})

        # -----------------------------
        # PROMPTS
        # -----------------------------
        if action == "explain":
            prompt = f"Explain clearly in simple words with examples:\n{user_input}"

        elif action == "summarize":
            prompt = f"Summarize the following in short bullet points:\n{user_input}"

        elif action == "flashcards":
            prompt = f"""
            Create exactly 5 clear flashcards on {user_input}.
            Each flashcard should have a Question and Answer.
            Return ONLY valid JSON in this format (use double quotes):

            [
              {{"question": "Question text", "answer": "Answer text"}}
            ]
            """

        elif action == "quiz":
            prompt = f"""
            Generate exactly 5 MCQ questions on {user_input}.
            Return ONLY valid JSON in this format (use double quotes):

            [
              {{"question": "Question text",
               "options": ["Option A", "Option B", "Option C", "Option D"],
               "answer": "Correct option exactly as written"}}
            ]
            """

        else:
            prompt = user_input

        # -----------------------------
        # CALL AI
        # -----------------------------
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful AI study assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
            )

            ai_output = completion.choices[0].message.content.strip()

            # -----------------------------
            # QUIZ GENERATION
            # -----------------------------
            if action == "quiz":
                try:
                    quiz_data = json.loads(ai_output)
                except json.JSONDecodeError:
                    return render(request, "index.html", {
                        "response": "Quiz generation failed. Please ensure the AI returns valid JSON.",
                        "user_input": user_input
                    })
                return render(request, "index.html", {
                    "quiz": quiz_data,
                    "user_input": user_input
                })

            # -----------------------------
            # FLASHCARDS
            # -----------------------------
            if action == "flashcards":
                try:
                    flashcards = json.loads(ai_output)
                except json.JSONDecodeError:
                    flashcards = [{"question": "Error generating flashcards", "answer": ""}]

            # -----------------------------
            # EXPLAIN / SUMMARIZE
            # -----------------------------
            response_text = ai_output

        except Exception as e:
            response_text = f"Error: {str(e)}"

    return render(request, "index.html", {
        "response": response_text,
        "flashcards": flashcards,
        "user_input": user_input
    })