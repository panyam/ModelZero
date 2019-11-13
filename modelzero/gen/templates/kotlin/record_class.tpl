
class {{class_name}} : AbstractEntity {
{%- for name, field in record_class.__record_fields__.items() %}
    var {{name}} : {{ gen.kotlintype_for(field.logical_type) }} 
        {#
        {%- if gen.is_optional_type(field.logical_type) %} =
        {{- gen.default_value_for(field.logical_type) }}
        {% endif %}
        #}
{%- endfor %}

    constructor(data : DataMap) {
        {%- for name, field in record_class.__record_fields__.items() %}
        {{ gen.code_for_member_extraction("data", name, field.logical_type) }}
        {% endfor %}
    }

    override fun toMap() : Map<String, Any?> {
        return mapOf(
        {%- for name, field in record_class.__record_fields__.items() -%}
            {%- if loop.index0 > 0 -%}, {%- endif -%}
            "{{name}}" to ensureAny({{ name }})
        {% endfor %})
    }
}
