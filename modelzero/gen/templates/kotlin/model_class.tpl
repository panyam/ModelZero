
class {{class_name}} : AbstractEntity {
{%- for name, field in model_class.__model_fields__.items() %}
    var {{name}} : {{ gen.kotlintype_for(field.logical_type) }} 
        {%- if gen.optional_type_of(field.logical_type) %} =
        {{- gen.default_value_for(field.logical_type) }}
        {% endif %}
{%- endfor %}

    constructor(data : DataMap) {
        {%- for name, field in model_class.__model_fields__.items() %}
        {{ gen.code_for_member_extraction("data", name, field.logical_type) }}
        {% endfor %}
    }

    override fun toMap() : Map<String, Any?> {
        return mapOf(
        {%- for name, field in model_class.__model_fields__.items() -%}
            {%- if loop.index0 > 0 -%}, {%- endif -%}
            "{{name}}" to ensureAny({{ name }})
        {% endfor %})
    }
}
