
class {{record_class.__name__}} 
{%- if bases %} :
    {%- for base in bases %} {%- if loop.index0 > 0 -%}, {%- endif -%} {{ base }} {% endfor %}
{%- endif -%}
{
{%- for name, field in record_class.__record_metadata__.items() %}
    var {{camelCase(name)}} : {{ gen.kotlin_sig_for(field.logical_type) }} 
        get() {
        {% if field.optional -%}
            val v = get("{{name}}", false)
            if (v == null) return null
        {% else -%}
            val v = get("{{name}}")!!
        {% endif -%}
            {% if gen.is_list_type(field.base_type) %}
            val value = (v as List<Any>).stream()
            {% else %}
            val value = v
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
        {%- for name, field in record_class.__record_metadata__.items() -%}
            {%- if loop.index0 > 0 -%}, {%- endif -%}
            "{{name}}" to ensureAny({{ camelCase(name) }})
        {% endfor %})
    }
}
