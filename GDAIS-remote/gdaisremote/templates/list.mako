# -*- coding: utf-8 -*-
<%inherit file="layout.mako"/>

<h1>Equipment List</h1>

<p>Select an equipment or click start to begin acquiring from that equipment.</p>

<ul id="equips">
  % if equips:
    % for equip in equips:
      <li>
        <span class="name">
          <a href="${request.route_url('view', equip=equip.name)}">${equip.name}</a>
        </span>
        <span class="actions">
          % if equip.running:
            running...
            [ <a href="${request.route_url('stop', equip=equip.name)}">stop</a> ]
          % else:
            [ <a href="${request.route_url('start', equip=equip.name)}">start</a> ]
          % endif
        </span>
      </li>
    % endfor
  % else:
    <li>There are no equipment definition files in database.</li>
  % endif
</ul>
