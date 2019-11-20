
class {{record_class.__name__}}(data: MutableDataMap = mutableMapOf()) : AbstractEntity(data) {
{%- for name, field in record_class.__record_fields__.items() %}
    var {{camelCase(name)}} : {{ gen.kotlin_sig_for(field.logical_type) }} 
        get() = get("{{name}}")!!
        set(value) {
            set("{{name}}", value)
        }
{%- endfor %}
    constructor(_data : JSONObject) : this(JSONObjectMap(_data))

    override fun toMap() : Map<String, Any?> {
        return mapOf(
        {%- for name, field in record_class.__record_fields__.items() -%}
            {%- if loop.index0 > 0 -%}, {%- endif -%}
            "{{name}}" to ensureAny({{ camelCase(name) }})
        {% endfor %})
    }
}
