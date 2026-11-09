"""The "NU Forms 2025" template: the Microsoft Forms survey the office used until Phase 5.

The Phase 5 survey keeps this form's distinctions and statements (D29), so its answers map
one-to-one onto the new item keys (R8.1.2). ``legacy`` is the option's wording in the Forms
export, which is how the importer recognises it.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.survey import SurveyItem, SurveyTemplate

KEY = "nu_forms_2025"
NAME_EN = "NU Forms 2025"
NAME_JA = "NU Forms 2025"
INQUIRIES, ACTIVITIES, SATISFACTION, COMMENTS = (
    "inquiries",
    "activities",
    "satisfaction",
    "comments",
)


@dataclass(frozen=True)
class ItemSpec:
    key: str
    question: str
    kind: str
    label_en: str
    label_ja: str
    legacy: str | None = None
    exclusive: bool = False
    external: bool = False


ITEMS: tuple[ItemSpec, ...] = (
    ItemSpec(
        "inq_media",
        INQUIRIES,
        "flag",
        "Journalists/media",
        "報道機関（記者・放送局など）",
        "Journalists/media",
        external=True,
    ),
    ItemSpec(
        "inq_researchers_nu",
        INQUIRIES,
        "flag",
        "Nagoya University faculty/researchers",
        "名古屋大学の教員・研究者",
        "Nagoya University faculty/researchers",
    ),
    ItemSpec(
        "inq_researchers_ext",
        INQUIRIES,
        "flag",
        "Faculty/researchers not affiliated with Nagoya University",
        "学外の教員・研究者",
        "Faculty/researchers not affiliated with Nagoya University",
        external=True,
    ),
    ItemSpec(
        "inq_students_nu",
        INQUIRIES,
        "flag",
        "Nagoya University students",
        "名古屋大学の学生",
        "Nagoya University students",
    ),
    ItemSpec(
        "inq_students_ext",
        INQUIRIES,
        "flag",
        "Students not affiliated with Nagoya University",
        "学外の学生",
        "Students not affiliated with Nagoya University",
        external=True,
    ),
    ItemSpec(
        "inq_companies",
        INQUIRIES,
        "flag",
        "Companies/businesses",
        "企業",
        "Companies/businesses",
        external=True,
    ),
    ItemSpec(
        "inq_public",
        INQUIRIES,
        "flag",
        "General public",
        "一般の方",
        "General public",
        external=True,
    ),
    ItemSpec("inq_none", INQUIRIES, "flag", "None", "特になし", "None", exclusive=True),
    ItemSpec(
        "act_presentation",
        ACTIVITIES,
        "flag",
        "Presentations/speaking engagements",
        "講演・発表",
        "Presentations/speaking engagements",
    ),
    ItemSpec("act_meeting", ACTIVITIES, "flag", "Visits/meetings", "訪問・面談", "Visits/meetings"),
    ItemSpec("act_collab", ACTIVITIES, "flag", "Joint research", "共同研究", "Joint research"),
    ItemSpec(
        "act_article", ACTIVITIES, "flag", "Essays/articles", "寄稿・記事の執筆", "Essays/articles"
    ),
    ItemSpec("act_none", ACTIVITIES, "flag", "None", "特になし", "None", exclusive=True),
    ItemSpec(
        "sat_process",
        SATISFACTION,
        "scale",
        "The production process was easy to understand and follow",
        "作成のプロセスはわかりやすく、進めやすかった",
    ),
    ItemSpec(
        "sat_accuracy",
        SATISFACTION,
        "scale",
        "The press release conveyed my research accurately",
        "プレスリリースは私の研究を正確に伝えていた",
    ),
    ItemSpec(
        "sat_understandability",
        SATISFACTION,
        "scale",
        "The press release was well written and easy to understand",
        "プレスリリースはよく書かれていて、わかりやすかった",
    ),
    ItemSpec(
        "comments",
        COMMENTS,
        "text",
        "Any comments about the English press release service or suggestions for improvements",
        "英文プレスリリースのサービスについて、ご意見や改善のご提案がありましたらご記入ください。",
    ),
)

# The agreement scale, low to high (R11.6), in the words a Forms export may use.
SCALE = {
    "strongly disagree": 1,
    "disagree": 2,
    "neither agree nor disagree": 3,
    "neither": 3,
    "agree": 4,
    "strongly agree": 5,
    "まったくそう思わない": 1,
    "全くそう思わない": 1,
    "そう思わない": 2,
    "どちらともいえない": 3,
    "どちらとも言えない": 3,
    "そう思う": 4,
    "強くそう思う": 5,
}

# This export only (R8.1.2): row #1 was the office's test, and #13, #23, #49 and #62 used the
# scale inverted (all three "Strongly disagree" meant "Strongly agree"; Daniel, 2026-11-07).
SKIPPED_IDS = {"1": "staff_test"}
INVERTED_IDS = frozenset({"13", "23", "49", "62"})


def items_of(question: str) -> list[ItemSpec]:
    return [item for item in ITEMS if item.question == question]


async def ensure_template(db: AsyncSession, institution_id: uuid.UUID) -> SurveyTemplate:
    """The template and its items, made on the first import. Never changed afterwards."""
    template = await db.scalar(
        select(SurveyTemplate).where(
            SurveyTemplate.institution_id == institution_id,
            SurveyTemplate.key == KEY,
            SurveyTemplate.version == 1,
        )
    )
    if template is not None:
        return template
    template = SurveyTemplate(
        institution_id=institution_id,
        key=KEY,
        version=1,
        name_en=NAME_EN,
        name_ja=NAME_JA,
        is_active=False,
    )
    db.add(template)
    await db.flush()
    for position, item in enumerate(ITEMS):
        db.add(
            SurveyItem(
                institution_id=institution_id,
                template_id=template.id,
                key=item.key,
                question=item.question,
                kind=item.kind,
                exclusive=item.exclusive,
                external=item.external,
                label_en=item.label_en,
                label_ja=item.label_ja,
                position=position,
            )
        )
    await db.flush()
    return template
