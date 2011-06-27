# -*- coding: utf-8 -*-
<%inherit file="layout.mako"/>

<h1>${equip.name}</h1>

<h2>Information</h2>
<ul>
  <li><strong>status:</strong> ${status}</li>
</ul>

<h2>Actions</h2>
<ul>
  <li>
% if equip.running:
<a href="${request.route_url('stop', equip=equip.name)}">Stop ${equip.name}</a>
% else:
<a href="${request.route_url('start', equip=equip.name)}">Start ${equip.name}</a>
% endif
  </li>
  <li><a href="${request.route_url('list')}">Back to equipment list</a></li>
</ul>

<h2>Debug</h2>
<ul>
  <li><strong>equip file path:</strong> ${equip_path}</li>
</ul>

