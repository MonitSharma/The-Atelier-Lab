## Models on ollama

| Model Size (Parameters) | Estimated Memory Required | Example Models | Recommended Hardware |
| :--- | :--- | :--- | :--- |
| **1B - 3B** | 2 GB - 4 GB | Qwen 2.5 (1.5B), Phi-3 (3.8B) | Any modern laptop, Raspberry Pi, basic CPU. |
| **7B - 9B** | 6 GB - 8 GB | Llama 3.1 (8B), Mistral (7B), Gemma 2 (9B) | 8GB+ VRAM GPU (RTX 3060/4060) or 8GB+ Unified Memory (Mac M1/M2/M3). |
| **13B - 14B** | 10 GB - 12 GB | Qwen 2.5 (14B) | 12GB+ VRAM GPU (RTX 3060 12GB / 4070) or 12GB+ Mac. |
| **30B - 34B** | 20 GB - 24 GB | Command R (35B), Yi (34B) | 24GB VRAM GPU (RTX 3090/4090) or 24GB+ Mac. |
| **70B - 72B** | 40 GB - 48 GB | Llama 3.1 (70B), Qwen 2.5 (72B) | Dual RTX 3090s/4090s, Mac Studio with 48GB+ Unified Memory, or heavy system RAM (CPU mode). |


## Phase. 0 

```
Agent = LLM + Instructions + State + Tools + Execution Loop 
```

```
User prompt
    ↓
Agent loop
    ↓
LLM decides what to do
    ↓
Runtime interprets the decision
    ↓
Runtime executes a tool
    ↓
Tool result is returned to the LLM
    ↓
LLM decides whether to act again or answer
```

We have to make a ReAct loop here, ReAct stands for reasoning and acting. In Atelier, the loop is described as:

```
perceive → plan → act → observe
```

### Percieve 
The model recieves the current state:
1. original user goal
2. system instructions
3. available tool descriptions
4. previous tools observations


### Plan

The model decides what the next step should be.

### Act 

The model chooses a tool and executes it.


### Observe

Your Python runtime executes the calculator and creates an observation:


## Phase 0 System

```
                         ┌──────────────────────┐
User goal ──────────────▶│      loop.py         │
                         │                      │
                         │  maintain messages   │
                         │  call model          │
                         │  parse output        │ 
                         │  execute tool        │
                         │  append observation  │
                         │  detect completion   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      brain.py        │
                         │                      │
                         │ local model client   │
                         │ Ollama or MLX        │
                         └──────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Local Qwen3-8B model │
                         └──────────────────────┘
                         
```


1. `brain.py` : It is a direct translational bridge between our python code and the local Ollama server. It exposes a single interface function `ask_model`  that allows agent to talk to the model.

2. `calculator.py` : Here we make use of Python's abstract syntax tree (`ast`) module to inspect and run the math safely.

3. **Division of Labor (LLM vs. Python Runtime)**:

| Step | Who Does It? | What Happens? | Example |
| :--- | :--- | :--- | :--- |
| **1. Request** | User | You ask the agent a math question. | *"What is 3817 * 94?"* |
| **2. Reasoning** | **LLM (Brain)** | The model reads the question and realizes: *"I cannot do this math reliably. I should use my `calculator` tool."* | Emits: `CALCULATE: 3817 * 94` |
| **3. Execution** | **Python (Hand)** | The `loop.py` script intercepts the model's text, extracts `3817 * 94`, and runs it through [calculator.py](file:///Users/monitsharma/code_projects/atelier/agent/calculator.py). | Evaluates and returns: `358798` |
| **4. Observation** | **Python (Hand)** | The execution result is appended to the chat history as a new message. | Added to chat: `Observation: 358798` |
| **5. Synthesis** | **LLM (Brain)** | The model reads the observation and formulates a conversational final answer. | Emits: *"3817 * 94 is 358798."* |


---

## Phase 1

```
Qwen asks for a tool
        ↓
Tool registry checks whether it exists
        ↓
Arguments are validated
        ↓
Correct tool is executed
        ↓
Structured result is returned
```


The architecture for Phase 1 becomes:

```
                    ┌───────────────┐
                    │     Qwen      │
                    └───────┬───────┘
                            │
                    structured tool call
                            │
                    ┌───────▼───────┐
                    │   agent loop   │
                    └───────┬───────┘
                            │
                     tool dispatcher
                            │
             ┌──────────────┼──────────────┐
             │              │              │
        ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
        │  files  │    │ code exec│    │ search  │
        └─────────┘    └──────────┘    └─────────┘
                            │
                       ┌────▼────┐
                       │  shell  │
                       └─────────┘
```


Now we have to add a function of `read_file`, so that our AI agent can read the file too but the model must not be allowed to read arbitrary files from the system, like

```
/Users/monitsharma/.ssh/id_rsa
```

This bad ,but

```
Project.md
agent/loop.py
tools/registry.py
```

this is good.

So the file tool should only read files inside the project workspace. So we will buld it. 
