from ipdb import set_trace

def ensure_login(world):
    def ensure_login_func(f):
        def worker_func(*args, **kwargs):
            from flask import request, redirect, Response
            channel = world.AuthEngine.get_request_member(request, nothrow = True)
            if not channel:
                login_url = "/auth/login/?to=%s" % request.url
                return redirect(login_url, code = 302)

            # Look for member
            # Only way we can be here is if via federated auth, 
            # but login otherwise wont succeed unless there is a registered account
            if False and not channel.memberkey:
                # Create a member with this user?
                assert channel.login_type == "gae"
                register_url = "/auth/gae/?to=%s" % request.url
                return redirect(register_url, code = 302)

            resp = f(*args, **kwargs)
            if type(resp) is str:
                resp = Response(resp)
            resp.set_cookie("logged_in_userid", str(channel.memberkey.value).encode('utf-8'))
            return resp
        # worker_func.func_name = f.func_name
        return worker_func
    return ensure_login_func

