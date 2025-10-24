# Phase 1 Write-Up: Meeting Summarizer Agent - Baseline Evaluation

## 1. Agent Selection and Justification

### 1.1 Why Meeting Summarizer Agent?

I selected a **Meeting Summarizer Agent** that uses Google's Gemini AI to extract structured information from meeting transcripts. This agent is ideal for evaluating context and memory management for several key reasons:

#### Context Length Variance
Meeting transcripts naturally vary in length, providing diverse context requirements:
- **Short contexts** (200-400 words): Daily standups, quick check-ins
- **Medium contexts** (400-800 words): Regular team meetings, sprint planning
- **Long contexts** (800-2000+ words): Quarterly planning, design reviews, all-hands meetings

This variance allows us to evaluate how the agent handles different context windows, which will be crucial for testing memory management improvements in Phase 2.

#### Memory Requirements
The task of summarizing meetings inherently requires context and memory:
- **Speaker attribution**: Remembering who said what throughout the conversation
- **Decision tracking**: Linking decisions to their context and rationale mentioned earlier
- **Action item ownership**: Connecting tasks to owners mentioned in different parts of the meeting
- **Risk identification**: Understanding implicit risks based on earlier statements
- **Cross-reference needs**: Understanding pronouns, references, and conversation flow

#### Structured Output Extraction
Unlike simple Q&A tasks, this agent must extract multiple structured elements:
- TL;DR summary
- Decisions with owners and context
- Action items with owners and due dates
- Identified risks and blockers
- Key discussion points

This complexity makes it easy to measure quality degradation when context is lost or memory is insufficient.

#### Real-World Applicability
Meeting summarization is a practical, widely-needed capability with:
- Clear evaluation metrics (extraction accuracy, completeness)
- Measurable performance (latency, success rate)
- Natural multi-session scenarios (multiple meetings per user)
- Obvious benefits from memory (learning user preferences, template recognition)

### 1.2 Baseline Characteristics (No Memory Management)

**Current Implementation:**
- ✅ Stateless processing: Each request is independent
- ✅ No conversation history retention
- ✅ No cross-session learning
- ✅ No context from previous meetings
- ✅ Single-turn interaction per transcript

This baseline is intentionally simple, making it perfect for:
1. Establishing performance benchmarks
2. Identifying limitations that memory management would solve
3. Measuring future improvements from context/memory enhancements

**Why This Baseline Needs Memory Management:**

Expected issues with current approach:
- Cannot learn user-specific terminology or preferences
- Cannot reference previous meetings or decisions
- Cannot maintain conversation context across multiple calls
- Cannot use historical data to improve extraction quality
- Limited by single-request context window

These limitations will become evident in the evaluation and justify Phase 2 enhancements.

---

## 2. Deployment Architecture

### 2.1 Infrastructure Design

**Platform:** AWS EC2 with Docker containerization

**Why EC2 + Docker:**
- ✅ Simple deployment without IAM complexity
- ✅ Cost-effective for research project (~$10-35/month)
- ✅ Full control over container orchestration
- ✅ Easy to scale horizontally (add more containers)
- ✅ Portable (works locally and in cloud)

**Why Not Other Options:**
- AWS Lambda: Cold start latency, 15-minute timeout limit problematic for long transcripts
- ECS/EKS: Overkill complexity, requires IAM roles
- Serverless: Harder to maintain session state, more expensive at scale
- Kubernetes: Too much overhead for 4 user containers

### 2.2 User and Session Isolation

**Architecture:**

```
┌──────────────────────────────────────────────────────┐
│                  EC2 Instance                        │
│                                                      │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │ User 1 (5001)   │  │ User 2 (5002)   │          │
│  │  ├─ Session A   │  │  ├─ Session A   │          │
│  │  └─ Session B   │  │  └─ Session B   │          │
│  └─────────────────┘  └─────────────────┘          │
│                                                      │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │ User 3 (5003)   │  │ User 4 (5004)   │          │
│  │  ├─ Session A   │  │  ├─ Session A   │          │
│  │  └─ Session B   │  │  └─ Session B   │          │
│  └─────────────────┘  └─────────────────┘          │
└──────────────────────────────────────────────────────┘
```

**Design Principles:**

1. **Different users → Separate containers**
   - Complete isolation (compute, memory, state)
   - Prevents cross-user contamination
   - Simulates production multi-tenancy
   - Each container has own Gemini API instance

2. **Same user, different sessions → Same container**
   - Sessions tracked via in-memory storage
   - Simulates multiple meetings by same user
   - Lower overhead than per-session containers
   - Realistic for single-user workload

3. **Port mapping**: User N → Port 500N
   - User 1: Port 5001
   - User 2: Port 5002
   - User 3: Port 5003
   - User 4: Port 5004

**Benefits:**
- ✅ Clear isolation boundaries
- ✅ Independent scaling per user
- ✅ Failure isolation (one user's crash doesn't affect others)
- ✅ Resource limits per user (future enhancement)
- ✅ Realistic production simulation

### 2.3 API Design

**RESTful API** with Flask:

```
GET  /health                        - Health check
POST /api/session/create           - Create new session
GET  /api/session/<id>             - Get session info
POST /api/summarize                - Summarize transcript
GET  /api/session/<id>/history     - Get session history
GET  /api/sessions                 - List all sessions
GET  /api/metrics                  - Get agent metrics
```

**Why REST API:**
- Simple, language-agnostic interface
- Easy to test with curl/Postman
- Standard HTTP for evaluation scripts
- Extensible for future features

**Session Management:**
- In-memory dictionary (acceptable for baseline)
- Session ID format: `{user_id}_{timestamp_ms}`
- Tracks requests per session for evaluation
- Future: Redis for persistence

---

## 3. Benchmark Design

### 3.1 Dataset Selection

**Primary Dataset:** AMI Meeting Corpus (from HuggingFace)
- Real meeting transcripts
- Natural conversational language
- Varying lengths and complexity
- Ground truth summaries available

**Fallback Dataset:** Synthetic Meeting Transcripts
- 5 carefully crafted scenarios
- Short, medium, and long examples
- Clear decisions, action items, and risks
- Consistent quality for reproducible testing

**Why AMI Dataset:**
- ✅ Real-world meeting conversations
- ✅ Natural context dependencies
- ✅ Varied speaker patterns
- ✅ Publicly available and free
- ✅ Large corpus for statistical significance

### 3.2 User Assignment Strategy

Transcripts are distributed to 4 users based on **context length**:

| User | Context Type | Word Range | Characteristics |
|------|--------------|------------|-----------------|
| User 1 | Short | 200-400 | Quick meetings, standup format |
| User 2 | Medium | 400-800 | Regular team meetings |
| User 3 | Long | 800-2000+ | Planning sessions, deep discussions |
| User 4 | Mixed | Varied | All types, testing adaptability |

**Rationale:**
- Tests agent performance across context lengths
- Simulates different user workload patterns
- Exposes context window limitations
- Identifies where memory would help most

### 3.3 Session Design

Each user has **2+ sessions**:
- Session A: First batch of transcripts
- Session B: Second batch of transcripts

**Purpose:**
- Test session isolation within user container
- Evaluate consistency across sessions
- Prepare for Phase 2 cross-session memory
- Measure if agent learns within container lifetime

### 3.4 Evaluation Metrics

#### Performance Metrics

1. **Latency (ms)**
   - Mean, median, P95, min, max
   - Measured per request
   - Plotted against context length

2. **Success Rate (%)**
   - Percentage of valid JSON responses
   - Per user and overall
   - Identifies reliability issues

3. **Throughput**
   - Requests per second (theoretical)
   - Total requests processed
   - Container resource utilization

#### Quality Metrics

1. **Extraction Counts**
   - Number of decisions extracted
   - Number of action items extracted
   - Number of risks identified
   - Average per meeting

2. **Completeness**
   - Percentage with TL;DR
   - Percentage with all fields populated
   - Missing data analysis

3. **Context Length Correlation**
   - Latency vs. word count
   - Quality vs. word count
   - Identify context window effects

#### User Isolation Metrics

1. **Per-User Performance**
   - Compare latencies across users
   - Compare success rates across users
   - Identify cross-user interference

2. **Session Independence**
   - Compare sessions within same user
   - Test consistency
   - Measure state leakage

### 3.5 Visualization

Generated plots:

1. **Latency vs Context Length** (scatter plot)
   - X-axis: Context length (words)
   - Y-axis: Latency (ms)
   - Color-coded by user
   - Shows scaling behavior

2. **Success Rate by User** (bar chart)
   - Compare reliability across users
   - Identify user-specific issues

3. **Latency CDF by User** (line chart)
   - Cumulative distribution functions
   - Shows P50, P95, P99 percentiles
   - Compare user performance distributions

4. **Extraction Counts** (bar chart)
   - Average decisions, actions, risks per meeting
   - Shows extraction effectiveness

---

## 4. Deployment Process

### 4.1 Manual Steps (Summary)

All steps provided in `DEPLOYMENT.md` and `QUICKSTART_EC2.md`. No automation scripts to allow manual control and learning.

**Key Steps:**
1. Launch EC2 instance (Ubuntu t2.medium)
2. Install Docker
3. Clone repository
4. Set Gemini API key
5. Build Docker image
6. Start 4 user containers
7. Load evaluation data
8. Run evaluation from local machine

**Why Manual:**
- ✅ User learns the architecture
- ✅ No hidden automation
- ✅ Full control over each step
- ✅ Easy to debug issues
- ✅ Meets requirement (no scripts)

### 4.2 No IAM Requirements

**Achieved by:**
- Using API key authentication (Gemini)
- No S3, DynamoDB, or other AWS services
- Direct EC2 + Docker only
- Simple port-based networking

### 4.3 Cost Optimization

**EC2 Instance:**
- t2.medium on-demand: ~$35/month
- t2.medium spot: ~$10/month (recommended)

**API Costs:**
- Gemini API free tier: 15 requests/minute
- Flash model: Very low cost

**Total:** $10-35/month for complete evaluation

---

## 5. Expected Results and Analysis

### 5.1 Baseline Performance Expectations

**Latency:**
- Short context (200-400 words): 1-3 seconds
- Medium context (400-800 words): 3-6 seconds
- Long context (800-2000 words): 6-15 seconds
- Expected linear scaling with context length

**Success Rate:**
- Target: >90% valid JSON responses
- Lower for very long transcripts (context overflow)

**Quality:**
- Should extract 1-5 decisions per meeting
- Should extract 2-8 action items per meeting
- Should identify 0-3 risks per meeting

### 5.2 Identified Limitations (What Memory Would Fix)

**Context Window Limitations:**
- Cannot process meetings longer than model limit
- Cannot split and reassemble long meetings
- Loses details at context boundary

**No Cross-Meeting Learning:**
- Cannot learn recurring meeting patterns
- Cannot use previous summaries to improve
- Cannot maintain project context across meetings

**No User Personalization:**
- Cannot learn user terminology preferences
- Cannot adapt to user's role or focus areas
- Cannot remember user's team structure

**No Session Continuity:**
- Cannot reference previous meetings
- Cannot track action item completion
- Cannot identify recurring risks

### 5.3 Justification for Phase 2

Phase 2 will address these limitations with:

1. **Vector Database** (ChromaDB/Pinecone)
   - Store meeting embeddings
   - Semantic search for relevant past meetings
   - Context retrieval for current summarization

2. **Long-Term Memory**
   - User preferences and terminology
   - Team structure and roles
   - Project context and history

3. **Cross-Session Context**
   - Reference previous meetings
   - Track decision outcomes
   - Identify patterns and trends

4. **Enhanced Evaluation**
   - Compare with/without memory
   - Measure accuracy improvements
   - Evaluate retrieval effectiveness
   - User satisfaction metrics

---

## 6. Reproducibility

### 6.1 Repository Structure

All code, configurations, and documentation in Git:
- `agent.py`: Core agent implementation
- `api.py`: REST API with user/session management
- `client.py`: API client for testing
- `evaluate_api.py`: Multi-user evaluation script
- `Dockerfile`: Container configuration
- `DEPLOYMENT.md`: Complete deployment guide
- `QUICKSTART_EC2.md`: Quick reference
- `WRITEUP.md`: This document

### 6.2 Data Availability

- AMI dataset: Public on HuggingFace
- Synthetic transcripts: Included in repository
- Results: Saved to `results/` directory

### 6.3 Evaluation Reproducibility

Complete evaluation can be reproduced by:
1. Following deployment steps in `DEPLOYMENT.md`
2. Running `python3 load_data.py` to load transcripts
3. Running `python3 evaluate_api.py http://ec2-ip:500`
4. Results saved to `results/api_evaluation.json` and plots

---

## 7. Conclusion

This Phase 1 implementation provides:

✅ **Working baseline agent** with clear limitations
✅ **Production-ready deployment** on EC2 with Docker
✅ **Multi-user isolation** with session management
✅ **Comprehensive evaluation** framework
✅ **Reproducible benchmarks** for Phase 2 comparison
✅ **Cost-effective** research infrastructure
✅ **Documented architecture** and justifications

The baseline evaluation will quantify current limitations and provide metrics to measure improvements when context and memory management are added in Phase 2. The infrastructure is ready to scale and supports seamless integration of vector databases and memory systems.

**Key Success Metrics for Phase 1:**
- ✓ Deploy 4 isolated user containers
- ✓ Process 20+ meeting transcripts
- ✓ Measure latency vs context length
- ✓ Evaluate extraction quality
- ✓ Document baseline performance
- ✓ Identify memory management needs

**Ready for Phase 2:**
- Add ChromaDB for semantic memory
- Implement cross-session context retrieval
- Add user preference learning
- Compare enhanced vs baseline performance
- Measure accuracy improvements
- Evaluate user satisfaction

