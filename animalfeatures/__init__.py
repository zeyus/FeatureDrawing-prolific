from sqlalchemy.ext.declarative import DeclarativeMeta  # type: ignore
from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, models, Page, ExtraModel, WaitPage  # type: ignore
from random import shuffle, randint, choice
import base64
import datetime


doc = """
A drawing experiment to help understand the motivation and purpose of the El Castillo animal depictions from the perspective of the producer.
"""

class AnnotationFreeMeta(DeclarativeMeta):
    """Metaclass to remove the __annotations__ attribute from the class
    this fixes an error where oTree tries to use __annotations__ and thinks it's a dict
    that needs saving.
    """

    def __new__(cls, name, bases, dct):
        dct.pop("__annotations__", None)
        return super().__new__(cls, name, bases, dct)

class C(BaseConstants):
    NAME_IN_URL = 'animalfeatures'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 16
    CONDITIONS = ['species_recognition', 'narrative', 'aesthetic']
    ANIMALS = ['horse', 'bison', 'ibex', 'deer']
    ANIMAL_ACTIONS = ['lie', 'run', 'stretch', 'walk']
    CONDITION_CONFIG = {
        'species_recognition': {
            'trial_title': 'Draw the selected animal so that another participant can easily recognize that it is this particular animal that you are communicating',
            'stim_dir': 'img/cond_r_a/',
            'by_animal': False,
        },
        'narrative': {
            'trial_title': 'Draw the selected animal so that another participant can easily recognize its behavior',
            'stim_dir': 'img/cond_n/',
            'by_animal': True,
        },
        'aesthetic': {
            'trial_title': 'Draw the selected animal so that another participant will find your drawing pleasing to the eye',
            'stim_dir': 'img/cond_r_a/',
            'by_animal': False,
        },
    }


def get_condition_config(condition: str):
    return C.CONDITION_CONFIG[condition]


class Subsession(BaseSubsession, metaclass=AnnotationFreeMeta):
    pass


class Group(BaseGroup, metaclass=AnnotationFreeMeta):
    pass


class Player(BasePlayer, metaclass=AnnotationFreeMeta):
    pass


class Drawing(ExtraModel, metaclass=AnnotationFreeMeta):
    subsess: Subsession = models.Link(Subsession)
    player: Player = models.Link(Player)
    trial: int = models.IntegerField()
    svg: str = models.LongStringField(initial="")  # type: ignore
    drawing_time: float = models.FloatField(initial=0.0)  # type: ignore
    start_timestamp: float = models.FloatField(initial=0.0)  # type: ignore
    end_timestamp: float = models.FloatField(initial=0.0)  # type: ignore
    trial: int = models.IntegerField(initial=0)  # type: ignore
    condition: str = models.StringField(initial="")  # type: ignore
    animal: int = models.StringField(initial="")  # type: ignore
    action: int = models.StringField(initial="")  # type: ignore


def creating_session(subsession):
    if subsession.round_number == 1:
        condition = None
        # if the condition is specified by the demo session (for testing) we will use that
        if 'condition' in subsession.session.config and subsession.session.config['condition'] is not None:
            condition = subsession.session.config['condition']
        # set up the condition for each participant
        for player in subsession.get_players():
            participant = player.participant
            # randomly select a condition if not specified
            participant.condition = choice(C.CONDITIONS) if condition is None else condition
            # set up the order of the stimuli
            stim_order = ['_'.join([animal, action]) for animal in C.ANIMALS for action in C.ANIMAL_ACTIONS]
            # randomize the order of the stimuli
            shuffle(stim_order)
            # save the order of the stimuli
            participant.stim_order = base64.b64encode(''.join(stim_order).encode()).decode()
            # set up the stimuli for this round
            for i in range(1, C.NUM_ROUNDS + 1):
                animal, action = stim_order.pop().split('_')
                Drawing.create(
                    subsess=subsession,
                    player=player,
                    trial=i,
                    condition=participant.condition,
                    animal=animal,
                    action=action,
                )

def get_current_trial(player: Player) -> Drawing:
    return Drawing.filter(subsess=player.subsession, player=player, trial=player.subsession.round_number)[0]


def get_stimuli_for_round(drawing: Drawing) -> list[dict]:
    selected_animal = drawing.animal
    selected_action = drawing.action
    condition = drawing.condition
    condition_config = get_condition_config(condition)
    stimuli = []
    file_ext = 'gif' if condition == 'narrative' else 'png'
    # if we display stimuli by animal, we will show all actions for that animal
    if condition_config['by_animal']:
        for action in C.ANIMAL_ACTIONS:
            stimuli.append({
                'animal': selected_animal,
                'action': action,
                'selected': action == selected_action,
                'class': 'selected' if action == selected_action else '',
                'stim': f"{condition_config['stim_dir']}{selected_animal}_{action}.{file_ext}",
            })
    # otherwise we will show all animals for the selected action
    else:
        for animal in C.ANIMALS:
            stimuli.append({
                'animal': animal,
                'action': selected_action,
                'selected': animal == selected_animal,
                'class': 'selected' if action == selected_action else '',
                'stim': f"{condition_config['stim_dir']}{animal}_{selected_action}.{file_ext}",
            })
    # shuffle the stimuli
    shuffle(stimuli)
    return stimuli




# PAGES
class Welcome(Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class Consent(Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class Instructions(Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class StimPage:
    @staticmethod
    def vars_for_template(player: Player):
        # get the current trial
        drawing = get_current_trial(player)
        # get the stimuli for this round
        stimuli = get_stimuli_for_round(drawing)
        # get the condition config
        condition_config = get_condition_config(player.participant.condition)
        return dict(
            page_title = condition_config['trial_title'],
            stimuli = stimuli,
        )


class Stimulus(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return StimPage.vars_for_template(player)


class Draw(Page):
    @staticmethod
    def vars_for_template(player: Player):
        # get the condition config
        condition_config = get_condition_config(player.participant.condition)
        return dict(
            page_title = condition_config['trial_title'],
        )
    
    @staticmethod
    def live_method(player, data):
        # get the current trial
        drawing = get_current_trial(player)
        if "event" in data:
            if data['event'] == 'init':
                # start the drawing timer
                if drawing.start_timestamp == 0.0:
                    drawing.start_timestamp = datetime.datetime.now().timestamp()
                drawing.drawing_time = datetime.datetime.now().timestamp() - trial.drawing.start_timestamp


class ThankYou(Page):
    @staticmethod
    # only display this page on the last round
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

page_sequence = [Welcome, Consent, Instructions, Stimulus, Draw, ThankYou]
