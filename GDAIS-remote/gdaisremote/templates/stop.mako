# -*- coding: utf-8 -*-
<%inherit file="layout.mako"/>

<h1>Stopping ${equip}</h1>
% if error:
    <p><strong>ERROR:</strong> ${str(error)}</p>
% else:
    <p>OK</p>
% endif
<p><a href="${request.route_url('list')}">Return to equipment list</a></p>
