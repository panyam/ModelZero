
class {{record_class.__name__}} : AbstractEntity {
{%- for name, field in record_class.__record_fields__.items() %}
    var {{camelCase(name)}} : {{ gen.kotlin_sig_for(field.logical_type) }} 
        get() {
        {% if field.optional -%}
            var value = get("{{name}}", false)
            if (value == null) return value
        {% else -%}
            var value = get("{{name}}")!!
        {% endif -%}
            {% if gen.is_list_type(field.logical_type) %}
            value = (value as List<Any>).stream()
            {% endif %}
            return {{ gen.any_to_typed(field.logical_type, "value") }}
        } 
        set(value) {
            set("{{name}}", value)
        }
{%- endfor %}
    // constructor(_data : JSONObject) : this(JSONObjectMap(_data))
    constructor(_data : Any) : super(_data)

    override fun toMap() : Map<String, Any?> {
        return mapOf(
        {%- for name, field in record_class.__record_fields__.items() -%}
            {%- if loop.index0 > 0 -%}, {%- endif -%}
            "{{name}}" to ensureAny({{ camelCase(name) }})
        {% endfor %})
    }
}
