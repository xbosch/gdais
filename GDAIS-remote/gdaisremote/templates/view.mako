# -*- coding: utf-8 -*-
<%inherit file="layout.mako"/>
<script src="${request.static_url('gdaisremote:static/datatables/js/jquery.js')}"></script>
<a name="page-top"></a>

<h1>${equip.name}</h1>

<ul id="nav" class="menu menu-horizontal">
  <li>
% if equip.running:
  <a class="stop" href="${request.route_url('stop', equip=equip.name)}">Stop ${equip.name}</a>
% else:
  <a class="start" href="${request.route_url('start', equip=equip.name)}">Start ${equip.name}</a>
% endif
  </li>
  <li><a href="#information">See equipment information</a></li>
  <li><a href="#messages">See log messages</a></li>
  <li><a href="#files">See acquired data files</a></li>
  <li><a class="back" href="${request.route_url('list')}">Back to equipment list</a></li>
</ul>

<h2 id="information">Information</h2>
<ul>
  <li><strong>status:</strong> ${status}</li>
  <li><strong>equip file path:</strong> ${equip_path}</li>
</ul>
<a href="#page-top">page top</a>
<hr />

<h2 id="messages">Messages</h2>
% if not equip.running:
  <p>GDAIS not running now. Showing last execution messages:</p>
% else:
  <p>Debug level:
    <select id="debug_level">
      % for l in log_levels:
        <option value="${l.num}" ${'selected' if l.default else ''}>${l.name}</option>
      % endfor
    </select>
  </p>
  <script>
    $('#debug_level').change(function() {
      $.get('/set_log_level/${equip.name}/'+$(this).attr('value'), function(data){
        if (data.status != "OK") { alert("ERROR: "+data.error); }
      });
    });
  </script>
% endif
<div id="dt">
  <div id="containter">
    <div class="dt_jui">
      <table id="logs" cellspacing="0" cellpadding="0" border="0" class="display">
        <thead>
          <tr>
            <th style="width: 85px">Date</th>
            <th style="width: 100px">Time</th>
            <th style="width: 250px">Module</th>
            <th style="width: 50px">Level</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script src="${request.static_url('gdaisremote:static/datatables/js/jquery.dataTables.js')}"></script>
<script>
  $.fn.dataTableExt.oApi.fnReloadAjax = function ( oSettings, sNewSource, fnCallback, bStandingRedraw )
  {
    if ( typeof sNewSource != 'undefined' && sNewSource != null )
    {
      oSettings.sAjaxSource = sNewSource;
    }
    this.oApi._fnProcessingDisplay( oSettings, true );
    var that = this;
    var iStart = oSettings._iDisplayStart;
    
    oSettings.fnServerData( oSettings.sAjaxSource, [], function(json) {
      /* Clear the old information from the table */
      that.oApi._fnClearTable( oSettings );
      
      /* Got the data - add it to the table */
      for ( var i=0 ; i<json.aaData.length ; i++ )
      {
        that.oApi._fnAddData( oSettings, json.aaData[i] );
      }
      
      oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
      that.fnDraw( that );
      
      if ( typeof bStandingRedraw != 'undefined' && bStandingRedraw === true )
      {
        oSettings._iDisplayStart = iStart;
        that.fnDraw( false );
      }
      
      that.oApi._fnProcessingDisplay( oSettings, false );
      
      /* Callback user function - for event handlers etc */
      if ( typeof fnCallback == 'function' && fnCallback != null )
      {
        fnCallback( oSettings );
      }
    }, oSettings );
  }

  var oTable;
  $(document).ready(function() {
    oTable = $('#logs').dataTable( {
      "bAutoWidth": false,
      "bDeferRender": true,
      "bJQueryUI": true,
      "bProcessing": true,
      "bStateSave": true,
      "sAjaxSource": '/view_log/${equip.name}',
      "sPaginationType": "full_numbers"
    });

% if equip.running: # only when new info may be added
    setInterval(function() {
      oTable.fnReloadAjax();
    }, 3000);
% endif

  });
</script>

<br />
<a href="#page-top">page top</a>

<hr />
<h2 id="files">Acquired data files</h2>
% if files:
<ul>
  % for file in files:
    <%
      date = file['date'].strftime('%Y%m%d')
      time = file['date'].strftime('%H%M%S')
      params = dict(equip=equip.name, date=date, time=time)
      download_url = request.route_url('download', **params)
      delete_url = request.route_url('delete', **params)
    %>
    <li>
      <a href="${download_url}">${file['date']}</a>
      [<a href="${delete_url}">delete</a>]
      ${file['size']}
    </li>
  % endfor
</ul>
% else:
  <p>No files found.</p>
% endif
<a href="#page-top">page top</a>

