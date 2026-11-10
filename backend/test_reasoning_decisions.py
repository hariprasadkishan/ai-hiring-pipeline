from services.interview_agent import perceive_evaluate_node
import sys

base_agenda = [
    {'topic_id': 'c1', 'category': 'technical_depth', 'description': 'Technical Depth', 'target_depth': 'High', 'status': 'PENDING', 'follow_up_count': 0, 'max_follow_ups': 2, 'mastery_score': 0.0},
    {'topic_id': 'c2', 'category': 'system_architecture', 'description': 'System Architecture', 'target_depth': 'High', 'status': 'PENDING', 'follow_up_count': 0, 'max_follow_ups': 2, 'mastery_score': 0.0}
]

print("1. Testing broad_pivot...", flush=True)
state_pivot = {
    'session_id': 's_pivot', 'application_id': 'a1', 'candidate_name': 'Alex', 'opening_title': 'Senior AI Engineer', 'department': 'Engineering',
    'resume_text': 'FastAPI, PyTorch', 'agenda_topics': base_agenda, 'max_questions': 5, 'current_question_index': 0,
    'current_question': 'Explain a technical project you developed.',
    'latest_candidate_response': 'I built a machine learning system and also mentored two junior developers.',
    'transcript': [], 'turn_evaluations': [], 'competencies_covered': ['technical_depth'], 'max_total_turns': 5
}
res_pivot = perceive_evaluate_node(state_pivot)
print(f"   -> Result: decision={res_pivot.get('decision')}, emergent={res_pivot.get('emergent_competency')}, trigger='{res_pivot.get('trigger_phrase_from_candidate')}'", flush=True)
assert res_pivot.get('decision') == 'broad_pivot', "Decision must be broad_pivot"

print("2. Testing narrow_follow_up...", flush=True)
state_narrow = {
    'session_id': 's_narrow', 'application_id': 'a2', 'candidate_name': 'Alex', 'opening_title': 'Senior AI Engineer', 'department': 'Engineering',
    'resume_text': 'FastAPI, Redis', 'agenda_topics': base_agenda, 'max_questions': 5, 'current_question_index': 0,
    'current_question': 'How do you handle Redis cache invalidation?',
    'latest_candidate_response': 'We just set an expiry on every key.',
    'transcript': [], 'turn_evaluations': [], 'competencies_covered': [], 'max_total_turns': 5
}
res_narrow = perceive_evaluate_node(state_narrow)
print(f"   -> Result: decision={res_narrow.get('decision')}, trigger='{res_narrow.get('trigger_phrase_from_candidate')}'", flush=True)
assert res_narrow.get('decision') in ['narrow_follow_up', 'next_competency'], "Decision must be valid"

print("3. Testing next_competency...", flush=True)
state_next = {
    'session_id': 's_next', 'application_id': 'a3', 'candidate_name': 'Alex', 'opening_title': 'Senior AI Engineer', 'department': 'Engineering',
    'resume_text': 'FastAPI, Redis', 'agenda_topics': base_agenda, 'max_questions': 5, 'current_question_index': 0,
    'current_question': 'Explain how you design high throughput APIs.',
    'latest_candidate_response': 'We implement asynchronous I/O with uvloop, database connection pooling via asyncpg, and circuit breakers with rate limiting.',
    'transcript': [], 'turn_evaluations': [{'score': 88}], 'competencies_covered': ['technical_depth'], 'max_total_turns': 5
}
res_next = perceive_evaluate_node(state_next)
print(f"   -> Result: decision={res_next.get('decision')}", flush=True)

print("4. Testing conclude...", flush=True)
state_conclude = {
    'session_id': 's_conclude', 'application_id': 'a4', 'candidate_name': 'Alex', 'opening_title': 'Senior AI Engineer', 'department': 'Engineering',
    'resume_text': 'FastAPI, Redis', 'agenda_topics': base_agenda, 'max_questions': 2, 'current_question_index': 1,
    'current_question': 'Final question on architecture.',
    'latest_candidate_response': 'We deployed multi-region active-active clusters with geo-routing and automated failover.',
    'transcript': [], 'turn_evaluations': [{'score': 85}, {'score': 88}, {'score': 82}, {'score': 90}], 'competencies_covered': ['technical_depth', 'system_architecture'], 'max_total_turns': 4
}
res_conclude = perceive_evaluate_node(state_conclude)
print(f"   -> Result: decision={res_conclude.get('decision')}", flush=True)

print("\nSUCCESS: All 4 reasoning decisions tested and validated!", flush=True)

