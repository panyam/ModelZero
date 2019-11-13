
fun {{ method.name }}({%- for name, param in method.kwargs.items() -%}
    {%- if loop.index0 > 0 %}, {% endif %}
    {{ name }}: {{gen.kotlintype_for(method.param_types[name])}}
{%- endfor %}) :
    {%- if method.return_type -%}
        Promise<{{ gen.kotlintype_for(method.return_type) }}, Exception>
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
        {%- if gen.is_list_type(method.return_type ) %}
            var out = it.jsonArray!!.stream<JSONObject>.map {
                {{ gen.converter_call(method.return_type.child_type, "it") }}
            }.collect(Collectors.toList())
        {% else %}
            var out = {{ gen.converter_call(method.return_type, "it") }}
        {%- endif %}
        Promise.of(out)
    }
}
