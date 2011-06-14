# -*- coding: utf-8 -*-
<%inherit file="layout.mako"/>

<h1>Equipment List</h1>

<ul id="equips">
  % if equips:
    % for equip in equips:
      <li>
        <span class="name">${equip}</span>
        <span class="actions">
          ${equip}
          [ <a href="${request.route_url('start', equip=equip)}">start</a> ]
        </span>
      </li>
    % endfor
  % else:
    <li>There are no equipment definition files in 'conf/equips' directory.</li>
  % endif
</ul>
