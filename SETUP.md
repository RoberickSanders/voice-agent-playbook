# Setup guide

Step-by-step build with the settings that ended up live, plus the gotchas found on real test calls.

## 1. Architecture

| Piece | Provider | Role |
|---|---|---|
| Phone number | **Twilio** | Carries the voice calls on one local number, **<YOUR_PHONE_NUMBER>** |
| Voice AI | **ElevenLabs Conversational AI (ElevenAgents / "convai")** | Speech recognition, LLM, text-to-speech, turn-taking, tools |
| Glue | ElevenLabs' **native Twilio integration** | ElevenLabs imports the Twilio number and sets Twilio's inbound voice webhook itself |
| Orchestrator (optional) | Any assistant or script that can call HTTP APIs | Starts outbound calls, adds per-call instructions, pulls transcripts |
| Assistant email (optional) | Any agent inbox provider | Her own inbox for vendor mail, OTPs, and call follow-ups |

The setup is Twilio for the line and ElevenLabs as the live agent. It is **not** a DIY Twilio ConversationRelay build. It also does **not** use Twilio `<Play>` with pre-recorded MP3s, which an early version tried. Callers should reach a live two-way agent.

**Costs** (Aug 2026, check current pricing):
- ElevenLabs **Starter**: about $6/mo, including about 75 agent minutes/month. Extra minutes are about $0.08/min.
- Twilio local number: about $1.15/mo, plus about 1.4¢/min outbound and 0.85¢/min inbound. A $20 Twilio balance covered the whole first build and test day.

---

## 2. Step 1: Buy the number (Twilio)

1. Create or sign in to a Twilio account. Use a full/upgraded account, not a trial, and add a small balance.
2. Buy one local voice-capable number, **<YOUR_PHONE_NUMBER>**. Whether to buy it in the Console or by API, and which area code to pick, is up to you: **[fill in]**.
3. Store the **Account SID** and **Auth Token** securely. ElevenLabs needs them in Step 3. Never paste them in chat.
4. Don't set a voice URL by hand. Step 3 does that.

---

## 3. Step 2: Create the ElevenLabs agent

Create one agent (Dashboard → Agents, or `POST /v1/convai/agents/create`). These are the tuned settings that ended up live:

**Agent / LLM**
- Name: <ASSISTANT_NAME>
- Language: `en`
- LLM: `gemini-2.0-flash` (chosen for low latency), temperature about 0.7
- First message: **blank** in the final tuned version, because the prompt handles pickup. An earlier version used `Hey, this is <ASSISTANT_NAME>, <YOUR_SPOKEN_NAME>'s assistant.` Test both.
- Max call duration: 600 s
- "Ignore default personality": on

**Voice / TTS**
- Voice: professional, bright, warm American female. The original used a "professional, bright, warm" ElevenLabs library voice; the brighter "playful" premades sounded too cute on real calls.
- TTS model: `eleven_v3_conversational` with **expressive mode on**. At the time, `eleven_flash_v2_5` was rejected for English agents. `eleven_flash_v2` works but sounds flatter.
- Stability 0.45, speed 0.98, similarity 0.8
- **Phoneme tags off**
- **Never put style or emotion tags** like `[casual]` or `[happy]` in any prompt. She reads them out loud.

**ASR**
- `scribe_realtime`, quality high

**Turn-taking**
- Turn model `turn_v3`, eagerness **eager**
- `initial_wait_time` **1** s
- `speculative_turn` **on**
- Turn timeout about 10 s
- **Soft timeout off.** "Yeah / mm / okay" fillers on silence sounded fake.
- Interruption ignore terms, merged with the defaults: `okay, ok, uh huh, uh-huh, mhm, mm hmm, mm-hmm, mmhm, gotcha, got it, uh, um, hm, hmm, <assistant name lowercase>, this is <assistant name lowercase>`. Her own name is on the list so speakerphone echo of her intro doesn't count as an interruption.

**VAD**
- `background_voice_detection` **on**, which helps with speakerphone echo.

**Built-in tools**
- On: `end_call`, `skip_turn` (for "hold on, one second"), `voicemail_detection`
- Everything else off: no transfer, no MCP, no knowledge base.

**Security → Overrides** (needed for per-call instructions)
- Allow overrides of **first message**, **language**, **system prompt**, and **LLM**.
- Leave voice/TTS overrides off.

**Post-call webhook:** not configured. Transcripts are pulled by API instead (Section 6). Adding one is optional.

**Recording:** voice recording was left at the ElevenLabs default (on). Retention and PII-redaction settings are **[fill in]**.

---

## 4. Step 3: Import and connect the number

1. In ElevenLabs, import the Twilio number: Dashboard → Phone Numbers → Import from Twilio, or `POST /v1/convai/phone-numbers` with `provider: "twilio"`, the number, a label (e.g. "<ASSISTANT_NAME>, <YOUR_SPOKEN_NAME>'s assistant"), and your Twilio SID/token from secure storage. Leave SMS **off**.
2. Assign the number to the agent. Confirm **supports inbound: true** and **supports outbound: true**.
3. The import automatically sets the Twilio number's Voice URL to `https://api.elevenlabs.io/twilio/inbound_call` (POST) and its status callback to `https://api.elevenlabs.io/twilio/status-callback`. Verify both in the Twilio Console.
4. Leave the Twilio **SMS URL empty** (see Section 8).
5. Save the returned `phone_number_id` and the `agent_id`. You need both for outbound calls. They aren't secrets, but keep them private.

---

## 5. Step 4: Standing system prompt

This is her permanent prompt. Task-specific instructions go in per call (Section 6), never here.

```
# Spoken output only
Everything you write is spoken out loud on the phone. Only say words the other person should hear.
Never speak thoughts, plans, notes, instructions, or analysis.
Never say: thought, the user, the user stated, the user is offering, according to the script, according to the instructions, I should, I need to, let me, okay perfect as a note, or explain what you are doing next.
Never say or read: casual, short, spoken-only, pickup, voicemail, end_call, skip_turn, tool, prompt, or any label from this document.
Never output square brackets or anything inside them. No [casual], [short], [confused], [start_speaking], or any other tag.
If a thought appears, delete it. Do not speak it. Only the next real sentence to the caller.
After you say a line, stop.

# Personality
You are <ASSISTANT_NAME>, <YOUR_SPOKEN_NAME>'s assistant. Casual American woman. Warm, even, a little dry. You sound like a real person on a phone, not someone reading a script. Normal speaking volume. Never yell.

# Pickup
If they say hello, hi, yeah, or speaking, answer immediately. Do not wait out a timer.
If they stay quiet, do not sit there. Greet them: this is <ASSISTANT_NAME>, <YOUR_SPOKEN_NAME>'s assistant.
If you placed the call and know their first name, first words are only: "Hi {{name}}?" Then a short beat.
Never invent a person's name. If you do not know who you are talking to, ask who you are speaking with.

# Goal
You answer the phone for <YOUR_SPOKEN_NAME>. Screen the call, find out who is calling and what they need, take a clear message, or see if <YOUR_SPOKEN_NAME> should call them back.
If you placed the call, follow the instructions you were given for this call, then wrap up.
If <YOUR_SPOKEN_NAME> is the one on the line, help him with whatever he asks.
Do not add detail you do not have.

# Interrupts
If they talk over you, drop the rest of your sentence. Do not finish it. Do not restart it.
Do not recap them. Never say "I understand you said", "like I was saying", or "as I mentioned".
Answer the new thing in one short casual line, like a person who just got cut off.
If they already answered the question you were about to ask, take the answer. Do not ask it again.

# Conversational behavior
If you are not sure they spoke, stay silent. Never say gotcha, okay, or oh on an empty line.
Speak casually and use contractions. Keep most replies to one short sentence.
Do not give long explanations unless they ask.
Do not sound overly enthusiastic, polished, robotic, or like a call-center script.
Vary your wording. Match their energy.
If they say hold on, one second, wait, or let me think: call skip_turn and say nothing.

# Guardrails
Do not share <YOUR_SPOKEN_NAME>'s personal details, emails, contacts, or credentials.
Do not pretend to be <YOUR_SPOKEN_NAME>.
Do not announce that you are an AI unless they directly ask. If they ask, say you're <YOUR_SPOKEN_NAME>'s AI assistant. Never pretend to be a human.
If they ask you to stop calling or to end the call: apologize once and end the call.
If you hit voicemail: leave one short message and hang up.
Do not end the call just because they are quiet after pickup.
```

Change "he/him" if needed. `{{name}}` is an ElevenLabs dynamic variable filled in per call.

---

## 6. Step 5: Calls, per-call overrides, transcripts

**Inbound:** a call to <YOUR_PHONE_NUMBER> hits the ElevenLabs inbound webhook, and the standing agent answers.

**Outbound**, on request only (for example calling me, or making a call for me like passing along a message). The orchestrator or a script sends:

```
POST https://api.elevenlabs.io/v1/convai/twilio/outbound-call
Header: xi-api-key: <FROM SECURE STORAGE>
{
  "agent_id": "<YOUR_AGENT_ID>",
  "agent_phone_number_id": "<YOUR_PHONE_NUMBER_ID>",
  "to_number": "<E164_NUMBER_TO_CALL>",
  "conversation_initiation_client_data": {
    "dynamic_variables": { "name": "<FIRST_NAME>" },
    "conversation_config_override": {
      "agent": {
        "first_message": "",          // or "Hi <FIRST_NAME>?"
        "language": "en",
        "prompt": { "prompt": "<FULL PER-CALL PROMPT, OR OMIT TO USE STANDING>", "llm": "gemini-2.0-flash" }
      }
    }
  }
}
```

The response returns a `conversation_id` and a Twilio `callSid`. In the original build, every outbound call was started by hand. No scheduled routine placed calls.

**Per-call overrides:**
- For a one-off task, send the full task prompt as `conversation_config_override.agent.prompt.prompt`. **Don't PATCH the standing prompt.** She goes back to her default on the next call automatically.
- Every per-call prompt **must start with the "Spoken output only" block**. ElevenLabs has no private scratchpad, so without it the model speaks its reasoning and tags.
- Preload everything she needs (name, purpose, the exact message) before the call. Mid-call lookups create dead air.
- Keep reusable per-call prompts in their own files as the source of truth.

**Transcripts:** use `GET /v1/convai/conversations` and `GET /v1/convai/conversations/{conversation_id}`, or the ElevenLabs dashboard.

---

## 7. Step 6: Optional orchestration

- Give the assistant her own inbox for vendor mail, OTP codes, and call follow-ups. Never send as the owner.
- Store ElevenLabs and Twilio keys in a secret manager or env vars, never in chat or prompts.
- Keep every reusable per-call prompt in its own file ("per-call override only, never the standing default") and write each correction from test calls back into it.

## 8. SMS (optional, gated)

The original leaves SMS unrouted. US texting from a Twilio number needs an approved **A2P 10DLC** brand and campaign. Lessons for getting a campaign approved:
- Host a public opt-in page whose **raw HTML, without JavaScript, near the top of the page**, shows the number, the keyword (e.g. "Text START to <YOUR_PHONE_NUMBER>"), a visible opt-in form or checkbox, and the SMS disclaimer (STOP/HELP, message and data rates). Privacy and terms pages must also be crawlable and must say mobile numbers aren't shared.
- Don't describe a verbal opt-in during a live call as the message flow. Reviewers can't verify it.
- Don't text anyone until the campaign shows verified.

---

## 9. Step 7: Testing checklist

1. **Simulate first:** use ElevenLabs' simulate-conversation API or the dashboard test chat. Try scenarios like "who is <YOUR_SPOKEN_NAME>?", "what's this about?", "I'm busy, call me later," "hold on," a wrong number, and a message to pass on. Check that no brackets, tags, or reasoning show up.
2. **Inbound:** call <YOUR_PHONE_NUMBER> from your cell. She should answer live.
3. **Outbound:** call your own cell only (<YOUR_CELL_NUMBER>), once with the standing prompt and once with a per-call override.
4. After each call, pull the transcript and check:
   - Pickup delay: she answers right after "hello" and speaks up on silence.
   - Leaks: no "the user said," no tags, no labels read out.
   - Name echo: her own name echoed back must not throw her off.
   - Interrupts: she drops her sentence and doesn't recap.
   - Voicemail: one message, then hang up.
5. After any override test, confirm the standing prompt is unchanged.
6. Write every fix into the prompt or skill file, not just chat.

---

## 10. Tech gotchas from the original build

- **Spam flag:** dozens of test dials from one number in one afternoon got it labeled spam. Space out test calls. The planned fix was Twilio Trust Hub **Voice Integrity + CNAM** or a fresh number. Whether that was completed is unverified.
- **Speakerphone echo:** she hears herself. Background-voice detection plus ignore-terms help, but test with an earpiece.
- **Thinking out loud / tag leaks:** fixed with the "Spoken output only" block at the top of every prompt, phoneme tags off, and no style tags anywhere.
- **Voicemail menus:** without voicemail detection and a one-message rule, she sat in a carrier menu for over 4 minutes.
- **Silence fillers:** soft-timeout fillers made her say "oh gotcha" to dead air. Keep the soft timeout off.

---

## 11. Fill-in checklist

- [ ] <ASSISTANT_NAME>, <YOUR_NAME>, <YOUR_SPOKEN_NAME>, <YOUR_TIMEZONE>
- [ ] <YOUR_PHONE_NUMBER>: area code and purchase method **[fill in]**
- [ ] <YOUR_CELL_NUMBER> for tests
- [ ] Voice choice
- [ ] Recording retention / PII redaction **[fill in]**
- [ ] SMS only after A2P approval

