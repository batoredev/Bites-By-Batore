"""Bites' own request understanding: turns what a person types into a checked Reading.

Week 1 item 1.6 in docs/EXECUTION_PLAN.md. The Reading is the planner's input; the planner
(planner.py) stays deterministic, so a misread can never break a hard rule, only ask or miss.

Files:
- reading.py         the Reading fields and their defaults (what "understood" means).
- frozen_test.jsonl  hand-written requests with the expected Reading. NEVER used for training;
                     it measures every version, including today's keyword reader.
- evaluate.py        scores any reader on the frozen test, field by field.

Labelling guide for the frozen test (and later the training data):
- categories: the category ids asked for (see categories.py). Empty when none is named.
- interests: specific dishes, cuisines or activities narrower than a category
  ("biryani", "dosa", "go karting", "pottery", "ice cream"). A bare category word such as
  "cafe", "movie", "bowling" or "park" is a category, not an interest.
- budget / budget_unit: the number in rupees ("2k" = 2000). Unit "person" for each/per head,
  "group" for total/for all of us; None when the text doesn't say which.
- time_of_day: morning, afternoon, evening, late_night or now.
- surprise: the person asks to be surprised or doesn't know what they want.
- out_of_scope: something Bites does not plan (events, scenic drives, other cities, stays).
"""
