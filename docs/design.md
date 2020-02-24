Normal flow of views
--------------------

Function views are pretty straightforward. However class-based views can be somewhat complex
to grasp so below we try to break down the original flow in order to be able and see how the
patching occurs.


Example

```python
class MyView(View):
    def get(self):  
      return None
```

Pseudocode

```python
def as_view(cls):
    def view(request):
        self = cls()
        return self.dispatch
    return view
```

The `as_view` is normally called when setting urlpatterns. By calling it the inner view
is returned that can be used at the request-response cycle (aka at runtime). The `dispatch`
function will at runtime call the appopriate class instance view to return a response.


Patching strategy
-----------------

**Requirements & constraints**

  - Can't patch directly class views since as demonstrated in the flow, the patching needs to act on
    an instance basis.

**Approach**

Based on the above, the patching needs to occur at run-time during the request-response cycle of each
request.

For up-to-date information look into the `patching` module.
