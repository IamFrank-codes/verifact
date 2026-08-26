from app.evidence.providers import EvidenceItem

FIXTURES = [
    {
        'keys': ['vaccines reduce hospitalization', 'vaccines reduce severe illness', 'covid vaccines reduce hospitalization'],
        'claim': 'COVID-19 vaccines reduce the risk of hospitalization from severe illness.',
        'verdict': 'Supported by Available Evidence',
        'explanation': 'The retained records from configured public-health institutions describe reduced risk of severe disease and hospitalization after vaccination. This is an evidence assessment based on the listed sources and dates, not a guarantee for every individual.',
        'evidence': [
            EvidenceItem('World Health Organization', 'https://www.who.int/news-room/feature-stories/detail/vaccine-efficacy-effectiveness-and-protection', '2024-05-17', 'Vaccines substantially reduce the risk of severe disease, hospitalization and death from COVID-19.', 'supporting', 'This public-health guidance directly supports the general claim about reduced hospitalization risk.', 'VeriFact local fixture'),
            EvidenceItem('Centers for Disease Control and Prevention', 'https://www.cdc.gov/covid/vaccines/stay-up-to-date.html', '2024-09-10', 'Staying up to date with COVID-19 vaccines is the best way to protect against serious illness, hospitalization, and death.', 'supporting', 'This public-health guidance independently supports the claim about protection from serious outcomes.', 'VeriFact local fixture')
        ]
    },
    {
        'keys': ['vitamin c cures covid', 'vitamin c cure covid-19', 'vitamin c permanently cures covid'],
        'claim': 'Vitamin C cures COVID-19.',
        'verdict': 'Contradicted by Available Evidence',
        'explanation': 'The retained public-health material does not identify vitamin C as a cure for COVID-19 and describes evidence-based prevention and treatment separately. This assessment is limited to the evidence listed below.',
        'evidence': [
            EvidenceItem('National Institutes of Health', 'https://www.covid19treatmentguidelines.nih.gov/therapies/supplements/vitamin-c/', '2024-02-29', 'There are insufficient data to recommend for or against the use of vitamin C for the treatment of COVID-19.', 'contradicting', 'The clinical guidance contradicts the categorical statement that vitamin C is a proven cure.', 'VeriFact local fixture'),
            EvidenceItem('World Health Organization', 'https://www.who.int/news-room/questions-and-answers/item/coronavirus-disease-covid-19', '2024-03-15', 'There is no specific medicine to prevent or treat COVID-19; care and approved treatments are used for people with severe illness.', 'contradicting', 'The guidance provides context that a categorical cure claim is not established by this source.', 'VeriFact local fixture')
        ]
    },
    {
        'keys': ['neptune diamond mining', 'diamonds mined on neptune'],
        'claim': 'Diamonds are currently being mined on Neptune.',
        'verdict': 'Insufficient Evidence',
        'explanation': 'VeriFact’s local evidence set did not return reliable, independently reviewable records that establish or directly contradict this claim. Insufficient evidence is not a finding that the claim is true or false.',
        'evidence': []
    }
]

def find_fixture(text: str) -> dict | None:
    normal = text.lower()
    for fixture in FIXTURES:
        if any(key in normal for key in fixture['keys']):
            return fixture
    return None

def generic_claim(text: str) -> dict:
    return {
        'claim': text.strip()[:1000],
        'verdict': 'Insufficient Evidence',
        'explanation': 'No deterministic local fixture matched this submission and no external evidence providers are enabled. VeriFact cannot draw a conclusion without retained, reviewable evidence.',
        'evidence': []
    }
