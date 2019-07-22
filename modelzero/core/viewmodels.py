
from modelzero.core.models import *

class Projection(Model):
    """ A projection on a model allows selection of one or more fields from a bunch of source entities. 
    Projections can be thought of as functions on models.
    """
    def __init__(self, sources):
        pass

class create_view_model(name, source_models, suppressions = None):

class ViewModel(Model):
    """
    A ViewModel is how one or more entities are represented in a view.   ViewModels and entities are a many to many relationship with a single view bound to multiple entities or multiple views bound to a single entities.
    """

    """
    The default form registry points to form class that is ot be used 
    as a default form for the entity when used as StructField
    """
    ViewModelRegistry = {}

    """
    The entities bound to this view model by a unique identifier
    This ID does not necessarily have to be the Key of the entity.
    """
    Bindings : Mapping[str, Type[Model]] = {}

    """
    The view fields/elements in this view model.   
    The fields can either be core fields or child ViewModel fields.
    """
    ViewFields = {}

    def __init__(self, parent = None):
        self.bindings = bindings
        self.parent = parent
