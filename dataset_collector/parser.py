import os
import re
import json
from typing import List, Dict

try:
    from .models import Message, ActionData, Example
except ImportError:
    from models import Message, ActionData, Example


class LogParser:
    def __init__(self, runs_dir: str):
        self.runs_dir = runs_dir

    def parse_all(self) -> Dict[str, List[Example]]:
        coder_examples: List[Example] = []
        manager_examples: List[Example] = []

        if not os.path.exists(self.runs_dir):
            return {"coder": [], "manager": []}

        for run_id in os.listdir(self.runs_dir):
            run_path = os.path.join(self.runs_dir, run_id)
            if not os.path.isdir(run_path):
                continue

            logs_path = os.path.join(run_path, "logs")
            if not os.path.exists(logs_path):
                continue

            coder_chat_path = os.path.join(logs_path, "coder_chat.md")
            if os.path.exists(coder_chat_path):
                coder_examples.extend(self._parse_chat_file(coder_chat_path))

            manager_chat_path = os.path.join(logs_path, "manager_chat.md")
            if os.path.exists(manager_chat_path):
                manager_examples.extend(self._parse_chat_file(manager_chat_path))

        return {"coder": coder_examples, "manager": manager_examples}

    def _parse_chat_file(self, file_path: str) -> List[Example]:
        examples: List[Example] = []
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        message_pattern = re.compile(r'^### (system|user|assistant) — (.*?)(\n|$)', re.MULTILINE)
        
        matches = list(message_pattern.finditer(content))
        
        messages: List[Message] = []
        for i in range(len(matches)):
            start = matches[i].end()
            end = matches[i+1].start() if i + 1 < len(matches) else len(content)
            
            role = matches[i].group(1)
            
            msg_content = content[start:end].strip()
            
            if msg_content.startswith("```") and msg_content.endswith("```"):
                 lines = msg_content.splitlines()
                 if len(lines) >= 2:
                     msg_content = "\n".join(lines[1:-1])
            
            messages.append(Message(role=role, content=msg_content))

        history: List[Message] = []
        
        for i, msg in enumerate(messages):
            if msg.role == 'assistant':
                try:
                    json_match = re.search(r'\{.*\}', msg.content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        action_data = json.loads(json_str)
                        
                        if "action" in action_data:
                            is_failed = False
                            if i + 1 < len(messages):
                                next_msg = messages[i+1]
                                if next_msg.role == 'system':
                                    lower_content = next_msg.content.lower()
                                    if "error" in lower_content or "failed" in lower_content or "exception" in lower_content:
                                        is_failed = True
                            
                            if not is_failed:
                                thought = action_data.get("thought", "")
                                complexity = len(thought)
                                
                                # Extract extra fields (everything except action and thought)
                                extra = {k: v for k, v in action_data.items() if k not in ("action", "thought")}
                                
                                examples.append(Example(
                                    x=list(history),
                                    y=action_data["action"],
                                    y_full=ActionData(
                                        action=action_data["action"],
                                        thought=thought,
                                        extra=extra
                                    ),
                                    complexity=complexity
                                ))
                except json.JSONDecodeError:
                    pass
            
            history.append(msg)
            
        return examples
