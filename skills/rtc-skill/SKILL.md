---
name: rtc-skill
description: Use this skill when the document type is RTC (Record 
of Rights, Tenancy and Crops). Activates when user uploads or 
mentions an RTC document.
---

# RTC Document Skill

## What is an RTC?
RTC stands for Record of Rights, Tenancy and Crops. It is the 
most important land document in Karnataka. It proves who owns 
the land, how big it is, and what crops are grown on it.

## Fields to Explain to the User
When you see an RTC document, explain these fields in plain English:

- **survey_number**: The unique ID of this piece of land on 
  government maps. Like a house address but for farmland.
- **owner_name**: The person the government recognizes as the 
  legal owner right now.
- **area_acres**: How big the land is in acres.
- **land_type**: Dry land (rain-fed) or wet land (irrigated). 
  Wet land is more valuable.
- **encumbrances**: Any loans or legal cases attached to this 
  land. If this says anything other than "None" — flag it 
  immediately as a warning.
- **issued_date**: When this document was printed. If older 
  than 3 years, tell the user to get a fresh copy.

## What to Check For
1. Does the owner name match what the family expects?
2. Does the survey number match their other documents?
3. Are there any encumbrances listed?
4. Is the issued date recent?

## What to Tell the User
Explain everything like you are talking to a farmer who has 
never seen a legal document before. No jargon. Simple sentences.