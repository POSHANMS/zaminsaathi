---
name: mutation-skill
description: Use this skill when the document type is MUTATION 
(Mutation Extract). Activates when user uploads or mentions a 
mutation document or ownership transfer record.
---

# Mutation Document Skill

## What is a Mutation Extract?
A mutation is a record that land ownership has changed hands — 
through sale, inheritance, gift, or court order. It updates 
the government records to show the new owner.

## Fields to Explain to the User
- **previous_owner**: Who owned the land before the transfer.
- **new_owner**: Who owns it now according to this document.
- **transfer_reason**: Why it changed hands — Sale, Inheritance, 
  Gift, Court Order. Each has different legal weight.
- **transfer_date**: When the actual transfer happened.
- **registration_number**: The official registration number 
  of this transfer. This can be verified at the sub-registrar 
  office.
- **survey_number**: The land this mutation applies to. 
  THIS MUST MATCH the survey number on the RTC exactly.

## What to Check For — Critical
1. Does the survey number EXACTLY match the RTC survey number?
   Even a small difference (142/3 vs 142/4) means a serious 
   problem — flag this immediately
2. Is the previous owner on this mutation the same as the 
   current owner on the RTC?
3. Is the registration number present? If missing, this 
   mutation may not be legally valid

## What to Tell the User
If you find a survey number mismatch — tell the user clearly:
"The survey number on your mutation document does not match 
your RTC. This is a serious discrepancy. Do not proceed with 
any sale or transaction until this is resolved at your 
local Tahsildar office."