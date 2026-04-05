# Happy Path Demo Script

## 📹 Recording

**Watch the demo:** https://share.vidyard.com/watch/FQDxx4Lz8HyshyKrDgABfM

This recording shows a complete successful call flow: greeting → phone number capture with digit confirmation → Google Sheets customer lookup → identity confirmation → claim status lookup → FAQ answers → natural call closing → live post-call log appearing in Google Sheets.

---

## Setup Before Recording
1. Ensure Google Sheet has a test customer:
   - Phone: `+15551234567`
   - First name: `Sarah`
   - Last name: `Johnson`
   - Claim status: `pending`
2. Open Google Sheets "interactions" tab in a visible browser tab
3. Start screen recording (show both the call interface and the Sheet)

## Script

**[Call begins]**

**Agent:** "Hi, thank you for calling Observe Insurance Claims Support. My name is Alex, and I'm here to help you today. To get started, could you please share the phone number associated with your account?"

**Caller:** "Hi, yes — my number is 555-123-4567."

**Agent:** *(lookup_caller tool fires)* "Great, I found your account. Just to confirm — am I speaking with Sarah Johnson?"

**Caller:** "Yes, that's me."

**Agent:** "Perfect, Sarah. Let me pull up your claim details. Your claim is currently being reviewed. Typically, the review process takes about five to seven business days. I know waiting can be stressful, but rest assured your claim is being handled. Would you like to know anything else in the meantime?"

**Caller:** "Yeah, actually — what if I need to submit more documents later? How do I do that?"

**Agent:** "Great question. You can submit documents through our online portal at observeinsurance.com/upload, or you can email them directly to support@observeinsurance.com. Either way, they'll be attached to your existing claim."

**Caller:** "Got it. And what are your office hours in case I need to call back?"

**Agent:** "Our office is open Monday through Friday, from 9 AM to 6 PM Eastern Time. You're always welcome to call back during those hours."

**Caller:** "Perfect, that's all I needed. Thanks!"

**Agent:** "You're very welcome, Sarah. Thank you for calling Observe Insurance. Have a wonderful day!"

**[Call ends]**

**[Point camera/screen to Google Sheets — new row appears in interactions tab]**
- Timestamp: (auto)
- Caller: Sarah Johnson
- Summary: "Caller Sarah Johnson inquired about her pending insurance claim status. She was informed of the 5-7 business day review timeline. She also asked about document submission options and office hours."
- Sentiment: positive
- Call ID: (VAPI ID)

## Key Points to Highlight
- Phone number normalization: caller said "555-123-4567" (no country code), system matched it correctly
- Natural conversation flow — agent didn't sound robotic
- FAQ answers were accurate and conversational
- Post-call log appeared in real-time in Google Sheets
