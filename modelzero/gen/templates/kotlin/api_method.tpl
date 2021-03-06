
fun {{ method.name }}({%- for name, param in method.kwargs.items() -%}
    {%- if loop.index0 > 0 %}, {% endif %}
    {{ name }}: {{gen.kotlin_sig_for(param_types[name])}}
{%- endfor %}) :
    {%- if return_type -%}
        Promise<{{ gen.kotlin_sig_for(return_type) }}, Exception>
    {%- else -%}
        Promise<Int, Exception>
    {%- endif -%} {
    var queryParams = mapOf<String, Any>(
    {%- for name, param in method.query_params.items() %}
        {%- if loop.index0 > 0 %}, {% endif %}
        "{{ name }}" to {{ name }}
    {% endfor -%}
    )

    {%- with name,param = method.body_param -%}
    {% if name %}
    var requestBody = httpClient.toJsonBody({{name}}.toMap())
    {% else %}
    var requestBody : RequestBody? = null
    {% endif -%}
    {% endwith -%}
    var request = httpClient.buildRequest("{{ http_method }}", "{{ path_prefix }}", queryParams, requestBody)
    return httpClient.sendRequest(request) bind {
        {%- if gen.is_list_type(return_type ) %}
            val results = (it.jsonArray!!).stream<JSONObject>()
        {% else %}
            val results = it.jsonObject!!
        {%- endif %}
        var out = {{ gen.any_to_typed(return_type, "results") }}
        Promise.of(out)
    }
}
