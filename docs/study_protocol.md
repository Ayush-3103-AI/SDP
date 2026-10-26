# Operator study protocol (FR-025)

Question: do explanations (cause set with probabilities, sensor flags, heatmap, gate reasons, counterfactual sentence)
make an operator pick the right correction more often than the bare detection does?
Reference effect: Senoner et al. 2024, +7.7 pp inspector accuracy with explanations (pre-registered).
Primary measure: accuracy = share of cards where the participant applied (or modified) the proposal for the run's
induced cause. Secondary: decision time, NASA-TLX (raw), 5-item trust scale.

## Design
- Within-subject, 2 blocks of 12 cards. One block has the explanation ON, the other OFF.
- Counterbalancing: even participant IDs do ON first, odd IDs do OFF first (`xqi.study.block_order`).
  Assign IDs 1, 2, 3, ... in order of arrival, so the two orders stay balanced.
- Cards: 24 campaign events (T-0041 runs) with a known cause, i.e. the run's cause in `docs/campaign.csv` explains the
  defect class (09 §Data label rule). Critical events and events without proposals are left out.
  The same seed (`--seed 0`) gives every participant the same two card sets; only the ON/OFF order changes,
  so each card set is seen under both conditions across participants.
- OFF card: crop (frame + box), defect class, severity and the proposal buttons (variable, from → to value).
  ON card adds the cause set with p, α, sensor flags, heatmap, verdict reason, gate checks and the counterfactual text.
- Prerequisite: the loop must store each event's crop (`defects.crop_path`). It does not yet, so a card shows no
  picture. Fix that before the T-0041 campaign, or the study has no frame to show.
- Run it: `uv run python -m xqi study --events runs --out reports/study/study.sqlite`.
  The page writes only to the `--out` file. It never touches the run stores or a printer.

## Recorded (study.sqlite)
- `choices`: participant, block, condition, position, run_id, defect_id, known_cause, choice
  (apply/modify/reject/pause/stop), proposal_id, chosen_cause, modified_delta, correct, decision_s, wall_iso.
  `decision_s` runs from the card appearing to the click.
- `surveys` (after each block): 6 NASA-TLX sliders (0–100, step 5; performance 0 = perfect) and 5 trust items
  (1 = strongly disagree … 7 = strongly agree):
  1. The system's proposals are reliable.
  2. I am confident in the system's proposals.
  3. I understand why the system proposed what it did.
  4. I can depend on the system to propose a safe correction.
  5. I would accept the system's proposals on a real print.

  [assumed] The trust items are adapted from Jian et al. 2000 and Hoffman et al. 2018. Not a validated short form.

## Consent text (read aloud, then the participant says "yes" or leaves)
> This is a study of a 3D-print monitoring tool, not a test of you. You will see 24 pictures of print defects and
> choose what you would do about each one. After every 12 pictures you answer two short questionnaires.
> It takes about 30 minutes. We record your choices, how long each one takes and your questionnaire answers under a
> number, not your name. Nothing you click is sent to a printer. You can stop at any time without giving a reason,
> and we will then delete your rows. Do you agree to take part?

## 30-minute script
| Min | Step |
|---|---|
| 0–3 | Welcome, consent text, assign the next participant ID. Note the ID and the date on paper only. |
| 3–8 | Briefing: the defect classes (one example picture each) and what the buttons mean: **Apply** sends the proposed setpoint change, **Modify** sends it with your own Δ, **Reject** does nothing, **Pause** pauses the print, **Stop** is the emergency stop (needs the tick box). "Pick the action you would take on a real print. Work at your normal pace." Do not mention explanations or what differs between the blocks. |
| 8–9 | Enter the ID, click **Start**. |
| 9–17 | Block 1 (12 cards). The facilitator sits behind and says nothing except "do what you would do". |
| 17–19 | Block 1 questionnaire (on screen). |
| 19–27 | Block 2 (12 cards). |
| 27–29 | Block 2 questionnaire. |
| 29–30 | Debrief: what the two blocks were, thanks. Ask them not to discuss it with other participants. |

## Exclusion rules (fixed before the first participant; apply them in analysis, never by deleting rows)
- Did not finish both blocks (fewer than 24 `choices` rows or 2 `surveys` rows): excluded.
- Took part in building or tuning the cause model, the gate or the cards (they know the answers): excluded.
  Team members may only run the pilot, and pilot rows are kept apart (`--out` a separate pilot file).
- Median `decision_s` under 2 s in either block (clicking through): excluded.
- The facilitator noted an interruption over 2 minutes during a block: that block is excluded.
- Any participant who saw the cards before (e.g. a second session): the second session is excluded.
- Report how many people were excluded under each rule.
