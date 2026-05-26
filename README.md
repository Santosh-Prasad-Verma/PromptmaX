<div align="center">

# 🌌 PROMPTX — NEURAL PROMPT PROTOCOL
**[ SYSTEM STATUS: OPERATIONAL ]**  
*The ultimate AI orchestration layer for precision-engineered instructions.*

<br/>

![PromptX Architecture](assets/architecture_diagram.png)

<br/>

[![GitHub stars](https://img.shields.io/github/stars/Santosh-Prasad-Verma/PromptX?style=for-the-badge&color=7C4DFF&labelColor=1A237E)](https://github.com/Santosh-Prasad-Verma/PromptX/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Santosh-Prasad-Verma/PromptX?style=for-the-badge&color=00B8D4&labelColor=006064)](https://github.com/Santosh-Prasad-Verma/PromptX/issues)
[![License](https://img.shields.io/github/license/Santosh-Prasad-Verma/PromptX?style=for-the-badge&color=00C853&labelColor=1B5E20)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

<br/>

**[ 🚀 Quick Start ](#-initialization-sequence) • [ 🧠 Core Features ](#-feature-matrix) • [ 🏗️ Tech Stack ](#-tech-stack) • [ 📡 API Reference ](#-api-gateways) • [ 📊 Quality Engine ](#-quality-intelligence)**

---

</div>

<br/>

## 🧬 NEURAL OVERVIEW

**PromptX** is a sophisticated AI-powered prompt enhancement ecosystem. It leverages a **9-stage neural pipeline** to dismantle raw, vague user inputs and reconstruct them into high-fidelity, professional instructions. By orchestrating multiple LLMs (Gemini, Groq, NVIDIA), PromptX ensures that your AI interactions are deterministic, structured, and consistently elite.

### ⚡ Core Value Proposition
- 🛠️ **Iterative Refinement**: Automated loops that polish prompts until they hit a near-perfect quality score.
- 🔄 **Autonomous Fallback**: Smart chain of command — if Gemini limits hit, Groq or NVIDIA take over instantly.
- 📐 **Structural Integrity**: Enforces strict personas, contexts, and constraints using the advanced CREATE algorithm.
- 🔬 **Quality Intelligence**: Real-time 6-dimension scoring with visual heatmap feedback.

<br/>

## 🏗️ THE PIPELINE ARCHITECTURE

Instead of simple wrappers, PromptX uses a multi-layered processing stack:

```markdown
  [ 📥 RAW INPUT ]
         │
         ▼
  ┌───────────────┐
  │ 1. VALIDATION │ ── Checks sanitization & security
  └───────┬───────┘
          │
  ┌───────▼───────┐
  │ 2. ANALYSIS   │ ── NLP-driven intent & domain detection
  └───────┬───────┘
          │
  ┌───────▼───────┐
  │ 3. CONTEXT    │ ── Injects relevant persona & background
  └───────┬───────┘
          │
  ┌───────▼───────┐
  │ 4. ENHANCE    │ ── Multi-model CREATE algorithm execution
  └───────┬───────┘
          │
  ┌───────▼───────┐
  │ 5. VALIDATE   │ ── Quality gating & structural verification
  └───────┬───────┘
          │
         ▼
  [ 📤 OPTIMIZED ]
```

<br/>

## ⚡ FEATURE MATRIX

| Module | Status | Capability |
| :--- | :---: | :--- |
| **CREATE Engine** | 🟢 | Advanced Prompt Engineering Algorithm |
| **Model Fallback** | 🟢 | Gemini ↔ Groq ↔ NVIDIA ↔ HF |
| **Analyzer** | 🟢 | 6-Dimension Linguistic Quality Heatmap |
| **A/B Testing** | 🟢 | Concise / Detailed / Structured Variants |
| **Web Search** | 🟢 | Real-time web-context injection |
| **Cyber UI** | 🟢 | Premium Dark-mode Platinum Interface |
| **Batch API** | 🟢 | Bulk prompt processing & comparison |

<br/>

## 🚀 INITIALIZATION SEQUENCE

### 📋 Prerequisites
- Python 3.8+
- [Gemini API Key](https://aistudio.google.com/apikey) (Primary)
- [Groq/NVIDIA Keys](https://console.groq.com/) (Optional Fallbacks)

### 🛠️ Step-by-Step Boot
1. **Clone & Enter**
   ```bash
   git clone https://github.com/Santosh-Prasad-Verma/PromptX.git
   cd PromptX
   ```

2. **Environment Setup**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Secrets**
   ```bash
   cp .env.example .env
   # Edit .env with your system keys
   ```

4. **Initialize Neural Core**
   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver  # Terminal 1
   ```

5. **Launch Terminal Interface**
   ```bash
   python app.py  # Terminal 2 - Flask API
   ```

<br/>

## 📡 API GATEWAYS

PromptX provides dual endpoints for maximum flexibility:

### 🔥 Flask API (`:5000`)
- `POST /api/enhance`: Basic prompt optimization.
- `POST /api/ab-test`: Generate three distinct style variants.
- `POST /api/quality-heatmap`: Get linguistic scoring.

### 🐍 Django Enterprise (`:8000`)
- `POST /api/v1/enhance/`: Full enterprise-grade pipeline.
- `POST /api/v1/batch-enhance/`: Process multiple prompts simultaneously.
- `POST /api/v1/validate/`: Fact-checking & structural validation.

<br/>

## 📊 QUALITY INTELLIGENCE

Every prompt is scored across 6 vital dimensions to ensure peak performance:

| Dimension | Description | Target |
| :--- | :--- | :---: |
| **Clarity** | Absence of ambiguous phrasing | 9+ |
| **Specificity** | Granularity of requirements | 8+ |
| **Structure** | Logical organization/formatting | 9+ |
| **Context** | Background & Persona depth | 8+ |
| **Constraints** | Boundaries & Forbidden actions | 7+ |
| **Format** | Precise output specification | 9+ |

<br/>

## 🏗️ TECH STACK

- **Logic Core**: Python 3.10+, Django, Flask
- **Intelligence**: Google Gemini 2.0, NVIDIA AI, Groq Llama 3
- **NLP Layer**: spaCy, TextBlob, tiktoken
- **Database**: SQLite / PostgreSQL with Django ORM
- **Visuals**: Next-gen CSS, Vanilla JavaScript, Framer inspirations

<br/>

## 🤝 CONTRIBUTION PROTOCOL

We welcome neural engineers! Please review the [CONTRIBUTING.md](CONTRIBUTING.md) for architectural guidelines and coding standards.

<br/>

---

<div align="center">

**PromptX • Built for the Elite AI Architect.**  
Distributed under the MIT License.

</div>
