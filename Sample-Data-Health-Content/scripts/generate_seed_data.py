import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA_ROOT = ROOT / "sample-data"

ARTICLES = [
    ("physical-01", "Gentle walking for everyday movement", "physical", ["hypertension", "sedentary"], "low", [], "vendor", True,
     "Gentle walking can be an accessible way to add movement to a sedentary day. A comfortable pace lets many people begin gradually without special equipment.",
     "Try a short, flat route at a pace where conversation remains comfortable. Add a few minutes only when the current routine feels manageable."),
    ("physical-02", "Low-impact movement at home", "physical", ["hypertension", "high_bmi"], "low", [], "Everwell", True,
     "Low-impact movement uses controlled motions and avoids jumping. A chair, clear floor space, and comfortable clothing can be enough to start.",
     "Choose a few simple seated or standing movements and take rests whenever needed. Keep the effort easy and stop if you feel unwell."),
    ("physical-03", "Building a steady walking habit", "physical", ["hypertension", "high_bmi", "sedentary"], "low", [], "vendor", True,
     "A steady walking habit is built through consistency rather than speed. Brief, repeatable walks can fit around work and other daily responsibilities.",
     "Link a brief walk to a regular activity, such as a lunch break. Select a safe, level route and increase duration slowly if it remains comfortable."),
    ("physical-04", "Small activity breaks for desk workers", "physical", ["sedentary", "high_bmi"], "low", [], "Everwell", True,
     "Long periods of sitting can be interrupted with light movement. Activity breaks do not need to be intense to create a more active daily pattern.",
     "Stand, stretch gently, or walk indoors for a few minutes between tasks. A reminder can help, but adapt the movement to your comfort and surroundings."),
    ("physical-05", "Choosing enjoyable low-impact exercise", "physical", ["high_bmi"], "medium", [], "vendor", True,
     "Enjoyment can make regular activity easier to sustain. Options such as relaxed cycling, water-based movement, or beginner classes may suit different preferences.",
     "Select an accessible activity and begin with a short session. Check that the setting and equipment feel comfortable, and build gradually rather than aiming for rapid progress."),
    ("physical-06", "A gradual return to regular activity", "physical", ["high_bmi", "prediabetes"], "low", [], "Everwell", True,
     "Returning to activity after a quiet period is best approached with patience. A simple schedule can reduce the temptation to do too much on the first day.",
     "Plan a few short sessions across the week, with recovery time between them. Track how the routine feels, not just distance or speed, and adjust as needed."),
    ("physical-07", "Simple strength movements for beginners", "physical", ["high_bmi"], "medium", [], "vendor", False,
     "Beginner strength practice can use body weight and controlled movements. The aim of this educational guide is to explain gradual practice, not prescribe an exercise plan.",
     "Learn comfortable movement patterns with light effort and rest. Consider qualified instruction if unsure how to perform an exercise safely."),
    ("physical-08", "High-intensity interval training overview", "physical", ["high_bmi", "sedentary"], "high", ["hypertension"], "vendor", True,
     "Interval training alternates periods of harder effort with recovery. This overview describes the format only; it is not a personalized exercise recommendation.",
     "High-effort exercise may not be appropriate for everyone. People with health concerns should discuss activity choices with a qualified health professional before trying intense exercise."),
    ("physical-09", "Fast-paced circuit training overview", "physical", ["high_bmi"], "high", ["hypertension"], "Everwell", True,
     "A circuit combines several exercises with limited rest. This article explains a common fitness format without suggesting that it is suitable for any particular reader.",
     "Circuits can involve strenuous effort. Do not treat this description as clearance to exercise; seek qualified guidance about individual limitations and safe activity."),
    ("physical-10", "Planning movement around a busy week", "physical", ["sedentary", "general"], "low", [], "vendor", True,
     "A busy schedule can make movement feel difficult to organize. Small, planned opportunities may be easier to repeat than a demanding all-or-nothing routine.",
     "Choose realistic times and activities that fit your week. Keep a simple record of what you tried, and revise the plan if it becomes uncomfortable or impractical."),
    ("mental-01", "A short breathing pause during a stressful day", "mental", ["stress"], "low", [], "vendor", True,
     "A quiet pause can help some people notice how they are feeling during a demanding day. Slow, comfortable breathing is one simple mindfulness exercise.",
     "Sit in a comfortable position and notice a few natural breaths without forcing them. Stop the exercise if it feels uncomfortable and return attention to the room."),
    ("mental-02", "Creating a calmer bedtime routine", "mental", ["poor_sleep", "stress"], "low", [], "Everwell", True,
     "A consistent wind-down routine can create a predictable transition toward bedtime. Sleep is affected by many factors, so a routine is not a cure for sleep problems.",
     "Try a relaxing, screen-light activity at a similar time each evening. Keep expectations flexible and note whether the routine feels helpful over several days."),
    ("mental-03", "Writing down worries before resting", "mental", ["stress", "poor_sleep"], "low", [], "vendor", True,
     "Some people find it useful to write down concerns before trying to rest. The goal is to set thoughts aside temporarily, not to solve every problem at bedtime.",
     "Spend a few minutes listing concerns and one small next step, if known. Put the note away afterward; seek support if worry is persistent or distressing."),
    ("mental-04", "Mindful attention for beginners", "mental", ["stress"], "low", [], "Everwell", True,
     "Mindfulness practice involves noticing present-moment experiences with curiosity. It can be brief and does not require clearing the mind or achieving a special state.",
     "Notice sounds, sensations, or breathing for a short period. If attention wanders, gently return to what you noticed. Choose another activity if this practice is uncomfortable."),
    ("mental-05", "Setting healthy boundaries at work", "mental", ["stress"], "low", [], "vendor", True,
     "Work boundaries can help clarify when tasks begin and end. Communication styles and workplace options differ, so examples may need adapting to each situation.",
     "Consider a small, respectful boundary such as a planned break or a clear end-of-day task list. Ask a trusted person for support if a conversation feels difficult."),
    ("mental-06", "Relaxation through gentle muscle release", "mental", ["stress", "poor_sleep"], "low", [], "Everwell", True,
     "Gentle relaxation practices invite awareness of tension and ease. They should remain comfortable and can be adapted or skipped if a movement causes discomfort.",
     "Try noticing whether your shoulders or hands feel tense, then let them rest naturally. There is no need to tighten muscles or follow a rigid sequence."),
    ("mental-07", "Making room for restorative breaks", "mental", ["stress", "sedentary"], "low", [], "vendor", True,
     "Brief breaks can provide space between demanding tasks. A restorative pause might involve quiet, fresh air, or a pleasant activity rather than productivity.",
     "Choose a short break that is available and genuinely restful. Return to tasks gradually, and remember that taking a break does not replace professional support when needed."),
    ("mental-08", "Keeping a simple sleep diary", "mental", ["poor_sleep"], "low", [], "Everwell", True,
     "A sleep diary can help someone notice broad patterns in bedtime, wake time, and daytime energy. It is an observation tool, not a way to diagnose a sleep condition.",
     "Record a few simple details for a limited period and look for patterns without judging individual nights. Bring persistent concerns to an appropriate health professional."),
    ("mental-09", "Finding support during a stressful period", "mental", ["stress"], "medium", [], "vendor", False,
     "Talking with a trusted person can make a difficult period feel less isolating. Different people prefer different kinds of support, and it is reasonable to ask for what would help.",
     "You might ask someone to listen, help organize a task, or point you toward a support service. If distress feels urgent or unsafe, contact local emergency or crisis support."),
    ("mental-10", "Gentle evening reflection", "mental", ["poor_sleep", "stress"], "low", [], "Everwell", True,
     "A brief evening reflection can help mark the end of a busy day. It can focus on ordinary observations rather than evaluating whether the day was successful.",
     "Note one thing you noticed and one task for tomorrow, then close the notebook. If reflection increases worry, choose a more relaxing activity instead."),
    ("wellbeing-01", "Balanced meals and prediabetes education", "wellbeing", ["prediabetes"], "low", [], "vendor", True,
     "This general education article explains how balanced meal patterns may support everyday well-being. Food needs vary, and this material does not provide a personal meal plan.",
     "Notice how meals combine familiar foods and consider practical options that fit culture, budget, and access. Ask a qualified health professional for individualized nutrition guidance."),
    ("wellbeing-02", "Understanding everyday carbohydrate choices", "wellbeing", ["prediabetes"], "low", [], "Everwell", True,
     "Carbohydrate-containing foods differ in taste, preparation, and how they fit into daily meals. This overview encourages informed questions rather than labeling foods as universally good or bad.",
     "Compare familiar options and consider which meals feel satisfying and practical. Individual glucose and nutrition needs differ; discuss personal questions with a qualified professional."),
    ("wellbeing-03", "Planning convenient nourishing lunches", "wellbeing", ["prediabetes", "high_bmi"], "low", [], "vendor", True,
     "A convenient lunch can include foods that provide energy and variety. Planning does not need elaborate recipes, special products, or a single ideal combination.",
     "Make a short list of affordable options available nearby or at home. Adapt portions and ingredients to preference and access, and seek individualized advice when needed."),
    ("wellbeing-04", "Small daily habits for general well-being", "wellbeing", ["general"], "low", [], "Everwell", True,
     "Well-being is influenced by many parts of daily life, including rest, connection, movement, and enjoyable activities. There is no single routine that works for everyone.",
     "Choose one manageable habit that matters to you and try it without expecting perfection. Reflect on whether it fits your circumstances and make changes when useful."),
    ("wellbeing-05", "Making hydration reminders work for you", "wellbeing", ["general"], "low", [], "vendor", True,
     "People's fluid needs and routines vary. A reminder can help some people remember drinks during a busy day, but it should not override medical guidance or individual needs.",
     "Try keeping a preferred drink within reach if that is suitable for you. Ask a qualified professional about fluid guidance if you have a condition that affects hydration."),
    ("wellbeing-06", "Planning small steps toward a personal goal", "wellbeing", ["high_bmi", "general"], "low", [], "Everwell", True,
     "A personal well-being goal can be easier to approach when it is specific and realistic. Progress may be uneven, and changing a goal is a normal part of planning.",
     "Choose a small action and a time to review how it went. Focus on what is within your control and seek support if a goal relates to health concerns."),
    ("wellbeing-07", "Building supportive social connections", "wellbeing", ["stress", "general"], "low", [], "vendor", True,
     "Supportive social contact can take many forms, from a short message to a shared activity. The right amount and style of connection differs from person to person.",
     "Consider reaching out to someone you trust in a way that feels comfortable. Community groups and support services may offer alternatives when personal networks are limited."),
    ("wellbeing-08", "Creating a restful home environment", "wellbeing", ["poor_sleep", "general"], "low", [], "Everwell", True,
     "A comfortable place to rest can support a calming routine, though housing conditions and personal circumstances are not always easy to change.",
     "If possible, try one small adjustment such as reducing clutter near the bed or dimming a light. Work with the options available and avoid treating environment changes as medical treatment."),
    ("wellbeing-09", "Recognizing when to seek health guidance", "wellbeing", ["hypertension", "prediabetes"], "medium", [], "vendor", False,
     "Health information online is general and cannot assess an individual's circumstances. A qualified health professional can help answer questions about measurements, symptoms, and next steps.",
     "Write down questions you would like to ask and use a trusted local health service. Seek urgent care for severe or sudden symptoms rather than relying on an article."),
    ("wellbeing-10", "Everyday self-care without perfection", "wellbeing", ["stress", "general"], "low", [], "Everwell", True,
     "Self-care can mean ordinary activities that support comfort, connection, or rest. It is not a test of discipline, and it cannot replace help for significant health concerns.",
     "Choose something accessible and kind to yourself, even if it takes only a few minutes. If a self-care idea does not help, you are free to try another approach."),
]

DEFAULTS = [
    ("default-physical", "General physical well-being", "physical"),
    ("default-mental", "General mental well-being", "mental"),
    ("default-wellbeing", "General well-being", "wellbeing"),
]

COMMON_CONTEXT = (
    "Use this information as a starting point for reflection, not as a checklist or a promise of results. "
    "People have different preferences, access to resources, abilities, and health circumstances. "
    "A small option that fits someone's ordinary routine may be more practical than a demanding plan. "
    "It is fine to pause, adapt an idea, or decide that it is not suitable. "
    "Articles cannot assess personal symptoms, diagnose a condition, or replace qualified care. "
    "For questions about individual health, medications, symptoms, or safe activity, ask an appropriate health professional. "
    "When trying a general well-being idea, notice comfort and stop if something feels wrong. "
    "The purpose is to share accessible background information and support informed conversations, not to prescribe a course of action."
)


def build_body(title: str, overview: str, practical: str) -> str:
    sections = [
        f"{title}. {overview}",
        f"Practical ideas. {practical}",
        f"Making it fit. {COMMON_CONTEXT}",
    ]
    body = "\n\n".join(sections)
    word_count = len(body.split())
    if not 150 <= word_count <= 300:
        raise ValueError(f"{title} has {word_count} words; expected 150-300.")
    return body


def main() -> None:
    records = []
    for article_id, title, category, tags, intensity, contraindications, source, approved, overview, practical in ARTICLES:
        records.append(
            {
                "id": article_id,
                "title": title,
                "body": build_body(title, overview, practical),
                "category": category,
                "condition_tags": tags,
                "intensity": intensity,
                "contraindications": contraindications,
                "source": source,
                "approved": approved,
                "is_default": False,
                "published_date": "2026-01-15",
            }
        )
    for article_id, title, category in DEFAULTS:
        records.append(
            {
                "id": article_id,
                "title": title,
                "body": build_body(
                    title,
                    "This general article offers a few neutral ideas for reflecting on everyday well-being, without assuming a particular need or goal.",
                    "Choose an activity that feels comfortable and accessible, or use the article as a starting point for questions to discuss with a trusted professional.",
                ),
                "category": category,
                "condition_tags": ["general"],
                "intensity": "low",
                "contraindications": [],
                "source": "vendor",
                "approved": True,
                "is_default": True,
                "published_date": "2026-01-15",
            }
        )
    path = SAMPLE_DATA_ROOT / "articles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} articles to {path}.")


if __name__ == "__main__":
    main()
