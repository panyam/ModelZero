
from typing import Union, Type, TypeVar
from flask_wtf import FlaskForm
from modelzero.core.entities import *
from wtforms.form import FormMeta
from wtforms import fields as wtfields
from modelzero.utils import with_metaclass

class ModelFormBase(FlaskForm):
    # The default form registry points to form class that is ot be used 
    # as a default form for the model when used as StructField
    FormRegistry = {}

    # The ModelClass for which this form is being rendered.
    ModelClass = None

    # A list of field paths to be suppressed in the final form
    SuppressPaths = None

    def __init__(self, *args, **kwargs):
        super(ModelFormBase, self).__init__(*args, **kwargs)

    @classmethod
    def form_field_for(cls, field):
        if issubclass(field.__class__, DateTimeField):
            return wtfields.DateTimeField()
        elif issubclass(field.__class__, StringField):
            return wtfields.StringField()
        elif issubclass(field.__class__, IntegerField):
            return wtfields.IntegerField()
        elif issubclass(field.__class__, LongField):
            return wtfields.IntegerField()
        elif issubclass(field.__class__, FloatField):
            return wtfields.FloatField()
        elif issubclass(field.__class__, BooleanField):
            return wtfields.BooleanField()
        elif issubclass(field.__class__, StructField):
            form_class = cls.form_class_for(field.model_class)
            formfield = wtfields.FormField(form_class)
            return formfield
        elif issubclass(field.__class__, ListField):
            child_field = cls.form_field_for(field.child_field)
            formfield = wtfields.FieldList(child_field)
            return formfield
        elif issubclass(field.__class__, KeyField):
            # - Need a better way to do this
            return wtfields.StringField()
        else:
            assert False, f"Invalid field class: {field.__class__} - {field.field_name}"

    @classmethod
    def form_class_for(cls, model_class):
        """ Returns the flask form class for a particular model class.
        If such a class does not already exist or is not registered, a 
        default one is created. """
        FormRegistry = cls.FormRegistry
        if model_class not in FormRegistry:
            NewForm = type(f"{model_class.__name__}Form",
                            (ModelForm,),
                            dict(ModelClass = model_class))
            FormRegistry[model_class] = NewForm
        return FormRegistry[model_class]

    @classmethod
    def load_model_fields(cls):
        eclass = cls.ModelClass
        model_fields = eclass.__model_fields__
        for field_name, field in model_fields.items():
            # Ensure field_name is not already defined
            if not hasattr(cls, field_name):
                setattr(cls, field_name, cls.form_field_for(field))

class ModelFormMeta(FormMeta):
    """ Form representation of entities.  """
    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)
        # Instead of replacing the form registry, merge them from parent
        parent_registry = getattr(x.__base__, "FormRegistry")
        this_registry = getattr(x, "FormRegistry")
        if parent_registry != this_registry:
            for k,v in parent_registry.items():
                if k not in this_registry:
                    this_registry[k] = v
        return x

    def __call__(cls, *args, **kwargs):
        # First ensure model class fields are set
        cls.load_model_fields()
        return FormMeta.__call__(cls, *args, **kwargs)

class ModelForm(with_metaclass(ModelFormMeta, ModelFormBase)):
    pass

def suppress_field_paths(form, paths):
    for path in paths:
        pass

class EngineFormBase(FlaskForm):
    EngineClass = None
    EngineMethod = None
    # A list of field paths to be suppressed in the final form
    SuppressPaths = None

    def __init__(self, *args, **kwargs):
        super(EngineFormBase, self).__init__(*args, **kwargs)

    @classmethod
    def load_engine_method_fields(cls):
        eclass = cls.EngineClass
        method_name = cls.EngineMethod
        import inspect
        method = getattr(eclass, method_name)
        signature = inspect.signature(method)
        method_params = signature.parameters
        # Ensure we have forms for all method params.  This needs two things:
        #   * The method needs an annotation.  If an annotation does not 
        #     exist and a field has not been manually specified, an error 
        #     is raised.
        #   * The annotation (for now) cannot be a TypeVariable for now as 
        #     this would require us to dig through parent bases to see what 
        #     the TypeVars resolve to.  So if that is the case we fall back 
        #     to a manual entry in the form.
        for name, param in method_params.items():
            # Ensure field_name is not already defined
            if name != "self" and not hasattr(cls, name):
                # Check the type
                if param.annotation.__class__ == TypeVar:
                    raise Exception(f"Field '{name}' is a TypeVar.  Please specify manually for now")
                else:
                    form_class = ModelFormBase.form_class_for(param.annotation)
                    form_field = wtfields.FormField(form_class)
                    setattr(cls, name, form_field)

class EngineFormMeta(FormMeta):
    """ Form for generating required fields out of the parameters of 
    a method. """
    def __call__(cls, *args, **kwargs):
        # Go through the engine's  method's parameters to see
        # what their types are and what validators they have on them
        cls.load_engine_method_fields()
        result = FormMeta.__call__(cls, *args, **kwargs)
        eclass = cls.EngineClass
        method_name = cls.EngineMethod
        import inspect
        method = getattr(eclass, method_name)
        signature = inspect.signature(method)
        method_params = signature.parameters
        validators = eclass.__service_methods__[method_name].validators
        set_trace()
        return result

class EngineForm(with_metaclass(EngineFormMeta, EngineFormBase)):
    pass
