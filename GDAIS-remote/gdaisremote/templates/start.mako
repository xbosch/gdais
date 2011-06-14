# -*- coding: utf-8 -*-
<%inherit file="layout.mako"/>

<h1>Starting ${equip}</h1>
<ul>
  <li><strong>equip file path:</strong> ${equip_path}</li>
  <li><strong>return code:</strong> ${retcode}</li>
</ul>
<p><a href="${request.route_url('stop', equip=equip)}">Stop ${equip}</a></p>
