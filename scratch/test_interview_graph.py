import asyncio
import os
import sys
import uuid

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.features.practice.langgraph.graph import (
    initialize_session_thread,
    submit_candidate_answer_thread,
)


async def run_test():
    session_id = str(uuid.uuid4())
    print(f"=== Starting Test Interview Session: {session_id} ===")

    # 1. Initialize session thread
    init_res = await initialize_session_thread(
        session_id=session_id,
        job_description="Senior Backend Engineer proficient in Python, FastAPI, PostgreSQL, and LangGraph AI agent design.",
        resume_text="5 years experience building distributed Python backends, microservices, and AI workflow automation.",
        difficulty="medium",
        max_topics=2,  # Short test run of 2 main topics
    )

    print("\n--- [Step 1: Session Initialized] ---")
    print(f"Initial Question: {init_res.get('current_question')}")
    print(f"Topic Count: {init_res.get('topic_count')}, Followup Count: {init_res.get('followup_count')}")

    # 2. Submit Turn 1 Answer
    print("\n--- [Step 2: Candidate Answer 1] ---")
    user_ans_1 = "I have built large scale FastAPI microservices with asyncpg and designed agent workflows using LangGraph checkpointers."
    ans_res_1 = await submit_candidate_answer_thread(session_id, user_ans_1)

    print(f"Last Decision: {ans_res_1.get('last_decision')}")
    print(f"Last Rating: {ans_res_1.get('last_rating')}/10.0")
    print(f"Feedback: {ans_res_1.get('last_feedback')}")
    print(f"Next Question: {ans_res_1.get('current_question')}")
    print(f"Topic Count: {ans_res_1.get('topic_count')}, Followup Count: {ans_res_1.get('followup_count')}")

    # 3. Submit Turn 2 Answer
    print("\n--- [Step 3: Candidate Answer 2] ---")
    user_ans_2 = "For context window management, I use Message graph trimming and state summaries so historical tokens don't overflow."
    ans_res_2 = await submit_candidate_answer_thread(session_id, user_ans_2)

    print(f"Last Decision: {ans_res_2.get('last_decision')}")
    print(f"Last Rating: {ans_res_2.get('last_rating')}/10.0")
    print(f"Status: {ans_res_2.get('session_status')}")
    if ans_res_2.get("final_report"):
        print(f"Final Report Overall Score: {ans_res_2['final_report'].get('overall_score')}")
        print(f"Final Summary: {ans_res_2['final_report'].get('final_summary')}")


if __name__ == "__main__":
    asyncio.run(run_test())
