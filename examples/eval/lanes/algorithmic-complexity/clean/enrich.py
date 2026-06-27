from typing import Dict, List


def filter_active_events(events: List[Dict], active_user_ids: List[str]) -> List[Dict]:
    active = set(active_user_ids)
    result = []
    for event in events:
        if event["user_id"] in active:
            result.append(event)
    return result
