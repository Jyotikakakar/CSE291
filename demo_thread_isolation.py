#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_with_memory import MeetingAgent

def print_section(title, char="="):
    print(f"\n{char*80}")
    print(f"  {title}")
    print(f"{char*80}\n")

def print_summary(result, meeting_num, team):
    if not result.get('success'):
        print(f"Error: {result.get('error')}")
        return
    
    summary = result['summary']
    
    print(f"{team} - Meeting {meeting_num}")
    print(f"   TL;DR: {summary.get('tldr', 'N/A')[:100]}...")
    print(f"   Latency: {result.get('latency_ms', 0):.0f}ms")
    
    # Context connections (shows thread isolation)
    if summary.get('context_connections'):
        print(f"\n   Context Connections ({len(summary['context_connections'])}):")
        for conn in summary['context_connections']:
            print(f"      - {conn.get('connection')}")
    else:
        print(f"\n   No context connections (first meeting in this thread)")
    
    # Decisions
    if summary.get('decisions'):
        print(f"\nDecisions ({len(summary['decisions'])}):")
        for d in summary['decisions'][:2]:
            print(f"      - {d.get('decision')} (Owner: {d.get('owner', 'N/A')})")
    
    # Action items
    if summary.get('action_items'):
        print(f"\n   Action Items ({len(summary['action_items'])}):")
        for a in summary['action_items'][:2]:
            related = " [RELATED TO PREVIOUS]" if a.get('related_to_previous') else ""
            print(f"      - {a.get('task')} (Owner: {a.get('owner', 'N/A')}){related}")
    
    print()

def main():
    print_section("TECH TEAM MEETINGS", "-")
    print("Thread ID: 'tech'")
    print("These meetings will only see context from other tech meetings.\n")
    
    tech_agent = MeetingAgent(use_memory=True, thread_id="tech")
    
    # Tech Meeting 1: Sprint Planning
    tech_meeting_1 = """
Alice: Good morning team. Let's plan our sprint for the mobile app backend.

Bob: I think we should focus on the API authentication layer first. We're getting security audit feedback.

Carol: Agree. The OAuth implementation needs work. I can lead that effort.

Alice: Perfect. Carol owns OAuth. Target is two weeks. Bob, what about the database schema?

Bob: I've designed the schema for user profiles and sessions. Ready to implement. Should take one week.

David: We also need to set up Redis for caching. Performance tests show we need it for scale.

Alice: Good point. David, you own Redis integration. One week timeline.

Carol: One risk - the OAuth provider API has been flaky. We might need a backup plan.

Alice: Let's schedule a checkpoint on Wednesday to assess OAuth progress. Any blockers?

Bob: We need staging environment access. DevOps hasn't provisioned it yet.

Alice: I'll follow up with DevOps today. Let's move forward. Sprint goal: OAuth, database schema, and Redis caching.
"""
    
    result = tech_agent.summarize(tech_meeting_1, use_context=True)
    print_summary(result, 1, "TECH TEAM")
    
    # Tech Meeting 2: Mid-Sprint Standup
    tech_meeting_2 = """
Alice: Quick standup. Carol, OAuth status?

Carol: OAuth integration is 70% done. The provider API issues we worried about haven't appeared yet. Should finish by tomorrow.

Alice: Excellent news. Bob, database?

Bob: Database schema is deployed to staging. Running migration scripts now. Found one issue with foreign key constraints that I'm fixing.

Alice: Timeline impact?

Bob: Minimal. Still on track for end of week.

David: Redis is integrated and tested. Cache hit rate is 85% in local testing. Ready to deploy to staging.

Alice: Great progress team. Carol, once OAuth is done, can you help Bob with the constraint issue?

Carol: Yes, I'll pair with him tomorrow afternoon.

Alice: Perfect. One concern - we haven't load tested yet. David, can you set up load tests for Monday?

David: On it. I'll use k6 for load testing.
"""
    
    result = tech_agent.summarize(tech_meeting_2, use_context=True)
    print_summary(result, 2, "TECH TEAM")
    
    
    print_section("MARKETING TEAM MEETINGS", "-")
    print("Thread ID: 'marketing'")
    print("These meetings will only see context from other marketing meetings.")
    print("NOTE: Should NOT reference any tech team meetings!\n")
    
    marketing_agent = MeetingAgent(use_memory=True, thread_id="marketing")
    
    # Marketing Meeting 1: Q4 Campaign Planning
    marketing_meeting_1 = """
Sarah: Welcome everyone. Let's plan our Q4 holiday campaign.

Tom: I've analyzed last year's data. Email campaigns had 24% open rate. Social media ads performed better at 3.2% CTR.

Emma: We should focus budget on Instagram and TikTok. Our demographic is most active there.

Sarah: Agreed. What's the creative concept?

Tom: I propose "Your Year, Elevated" as the tagline. Focuses on personal achievement and our product helping them succeed.

Emma: Love it. We can create user-generated content around that theme. Encourage customers to share success stories.

Sarah: Excellent. Timeline?

Tom: Campaign launches December 1st. We need creative assets by November 20th. Budget is $150K.

Emma: I'll coordinate with the design team. We need video ads, static posts, and email templates.

Sarah: Any risks?

Tom: Competition is launching similar campaigns. We need to move fast and be distinctive.

Sarah: Let's add influencer partnerships. Emma, reach out to our top 5 influencers by Friday.

Emma: Will do. Should we offer them commission or flat fee?

Sarah: Commission-based. Aligns incentives. Tom, you own the campaign metrics dashboard.

Tom: On it. I'll track daily engagement, conversion rates, and ROI.
"""
    
    result = marketing_agent.summarize(marketing_meeting_1, use_context=True)
    print_summary(result, 1, "MARKETING TEAM")
    
    # Marketing Meeting 2: Campaign Launch Review
    marketing_meeting_2 = """
Sarah: Week one results are in. Tom, walk us through the numbers.

Tom: Email campaign exceeded expectations. 31% open rate, up from our 24% target. Click-through is 4.8%.

Emma: Social media is performing well. Instagram ads at 3.8% CTR. TikTok is slightly lower at 2.9% but engagement is high.

Sarah: What about conversions?

Tom: Conversion rate is 2.1%. We're tracking to hit our $500K revenue target for Q4.

Emma: Influencer partnerships are working. Three of our five influencers have posted. Combined reach of 2M people.

Sarah: Impressive. What's not working?

Tom: Twitter ads are underperforming. Only 1.2% CTR. I recommend reallocating that budget to Instagram.

Sarah: Agreed. Make that change today. Emma, what about the user-generated content?

Emma: We've received 47 submissions so far. Quality is good. I'm featuring the best ones on our Instagram story.

Sarah: Let's amplify this. Tom, can we create a landing page showcasing all submissions?

Tom: Yes, I'll have it ready by Monday. Should boost credibility and encourage more submissions.

Sarah: Perfect. Keep this momentum going team.
"""
    
    result = marketing_agent.summarize(marketing_meeting_2, use_context=True)
    print_summary(result, 2, "MARKETING TEAM")

    
    print_section("MANAGEMENT TEAM MEETINGS", "-")
    print("Thread ID: 'management'")
    print("These meetings will only see context from other management meetings.")
    print("NOTE: Should NOT reference tech or marketing meetings!\n")
    
    management_agent = MeetingAgent(use_memory=True, thread_id="management")
    
    # Management Meeting 1: Q4 Business Review
    management_meeting_1 = """
Jennifer: Good morning leadership team. Let's review Q4 strategy and resource allocation.

Michael: Q3 revenue was $2.4M, 18% growth. We're projecting $2.8M for Q4 if current trends hold.

Lisa: Sales pipeline is strong. We have $1.2M in qualified opportunities. Close rate has improved to 32%.

Jennifer: Excellent. What about expenses?

Michael: Operating expenses are at $1.8M per quarter. Biggest items are engineering salaries at $800K and marketing spend at $400K.

Jennifer: Those seem reasonable given our growth. Lisa, what's your confidence level on the $2.8M projection?

Lisa: High confidence. Enterprise deals are accelerating. We signed three new contracts last week worth $350K annually.

Jennifer: Outstanding. What risks should we be aware of?

Michael: Burn rate. We're at $600K per quarter loss currently. Our runway is 18 months with current cash reserves.

Jennifer: When do we break even?

Michael: If revenue growth continues at 18% quarterly, we break even in Q2 2025.

Lisa: I need to hire two more account executives to capture the opportunity. Cost is $200K per year per person.

Jennifer: Approved. Hire those AEs. Any other resource needs?

Lisa: Customer success needs one more person. We're at capacity with current client base.

Jennifer: Make it happen. We can't compromise on customer experience.
"""
    
    result = management_agent.summarize(management_meeting_1, use_context=True)
    print_summary(result, 1, "MANAGEMENT TEAM")
    
    # Management Meeting 2: Year-End Planning
    management_meeting_2 = """
Jennifer: Let's finalize our 2025 plan. Michael, start with financials.

Michael: Q4 is tracking to $3.1M, ahead of our $2.8M projection. For 2025, I'm modeling $15M annual revenue.

Lisa: That's aggressive but achievable. Our new AEs are ramping well. We've closed $400K in new ARR this month alone.

Jennifer: Headcount plan?

Michael: We're at 45 people today. Plan is 60 people by end of 2025. Engineering will grow from 20 to 28.

Jennifer: Engineering growth is critical. Can we attract that talent?

Lisa: Market is competitive. We might need to increase comp packages. I recommend a 15% bump in engineering salaries.

Michael: That adds $300K annually. We can absorb it if revenue targets are met.

Jennifer: Approved. We need top talent. What about fundraising?

Michael: We should raise Series A in Q2 2025. Target is $10M to $15M.

Jennifer: Valuation expectations?

Michael: Based on our growth rate, we should get $50M to $60M post-money valuation.

Lisa: We need to show strong Q1 2025 results for that valuation.

Jennifer: Agreed. Let's make Q1 our best quarter yet.
"""
    
    result = management_agent.summarize(management_meeting_2, use_context=True)
    print_summary(result, 2, "MANAGEMENT TEAM")
    
    print_section("BACK TO TECH TEAM (Meeting 3)", "-")
    print("Thread ID: 'tech'")
    print("This meeting should reference Tech Meetings 1 & 2")
    print("Should NOT reference Marketing or Management meetings!\n")
    
    # Tech Meeting 3: Sprint Retrospective
    tech_meeting_3 = """
Alice: Sprint retro time. What went well?

Bob: We hit all our targets. OAuth is live, database schema is solid, Redis is performing great.

Carol: Collaboration was excellent. Pairing with Bob on the constraint issue saved us a day.

David: Load tests showed impressive results. We can handle 10K concurrent users with current setup.

Alice: Outstanding work. What could be improved?

Carol: We should have involved QA earlier. We caught some edge cases late in the sprint.

Bob: Agreed. Also, documentation was rushed at the end. We should document as we code.

Alice: Good points. Next sprint, let's have QA shadow us from day one.

David: One more thing - we need better monitoring. I want to set up Datadog.

Alice: Add that to next sprint backlog. Overall, great sprint team.
"""
    
    result = tech_agent.summarize(tech_meeting_3, use_context=True)
    print_summary(result, 3, "TECH TEAM")
    
    
    print_section("THREAD ISOLATION VERIFICATION", "=")
    
    print("Memory Summary by Thread:\n")
    
    for thread_id, agent in [("tech", tech_agent), ("marketing", marketing_agent), ("management", management_agent)]:
        memory = agent.get_memory_summary()
        print(f"Thread: {thread_id}")
        print(f"  Total meetings: {memory.get('total_meetings', 0)}")
        print(f"  Key people: {', '.join(memory.get('key_people', [])[:5])}")
        print(f"  Action items: {memory.get('recent_action_items', 0)}")
        print(f"  Decisions: {memory.get('recent_decisions', 0)}")
        print()
    
    
    print("Memory stored in:")
    print("   - memory_store/tech/")
    print("   - memory_store/marketing/")
    print("   - memory_store/management/")
    print()


if __name__ == "__main__":
    main()