# Error/Fallback Path Demo Script

## 📹 Recording

**Watch the demo:** https://share.vidyard.com/watch/pwQChg5XaAjpWMgJt2WFzc

This recording shows the graceful error path: greeting → phone number capture → lookup returns "not found" → agent gracefully offers a callback instead of bluffing → warm closing → interaction still logged to Google Sheets with "Unknown" caller and "neutral" sentiment. Demonstrates the no-hallucination guardrail and graceful degradation.

---

## Setup Before Recording
1. Ensure `+15559999999` does NOT exist in the customers sheet
2. Open Google Sheets "interactions" tab in a visible browser tab
3. Start screen recording

## Script

**[Call begins]**

**Agent:** "Hi, thank you for calling InsureCo Claims Support. My name is Alex, and I'm here to help you today. To get started, could you please share the phone number associated with your account?"

**Caller:** "Sure, it's 555-999-9999."

**Agent:** *(lookup_caller returns not found)* "I wasn't able to find an account with that number. Could you double-check the number and try again?"

**Caller:** "Hmm, maybe try 555-888-7777."

**Agent:** *(second lookup_caller, also not found)* "Unfortunately, I'm still not able to locate an account with that number either. I want to make sure you're taken care of, so let me schedule a callback from one of our representatives within one business day. They'll be able to look into this further for you. Is the number you called from the best one to reach you at?"

**Caller:** "Yeah, that works."

**Agent:** "Perfect, you're all set. A representative will reach out to you within one business day. Is there anything else I can help with in the meantime?"

**Caller:** "No, that's it. Thanks."

**Agent:** "Thank you for calling InsureCo. Have a wonderful day!"

**[Call ends]**

**[Point camera/screen to Google Sheets — new row appears]**
- Timestamp: (auto)
- Caller: Unknown
- Summary: "Caller attempted to check their claim status but could not be authenticated. Phone number +15559999999 was not found in the system, and the caller's last name (Martinez) could not be matched. A human representative callback was scheduled."
- Sentiment: neutral
- Call ID: (VAPI ID)

## Key Points to Highlight
- Graceful degradation — agent never panicked or gave a generic error
- Two verification attempts before escalating (phone number, then last name)
- Human callback offered proactively
- Interaction still logged even when caller is "Unknown"
- Sentiment correctly inferred as "neutral" (caller was calm but unresolved)
