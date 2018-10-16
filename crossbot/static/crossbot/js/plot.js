function setDefaultDates() {
  var d = new Date();

  function toVal(date) {
    return date.toISOString().split('T')[0];
  }

  $('#plot-settings input[name="end-date"]').val(toVal(d));
  d.setDate(d.getDate() - 10);
  $('#plot-settings input[name="start-date"]').val(toVal(d));
}

var timeData = {
  // date -> userstr -> time
};


function processJSON(data) {
  window.data = data;

  var users = new Set();
  var minDate = null;
  var maxDate = null;

  for (var time of data) {
    time = time.fields;

    var date = time.date;
    if (minDate == null || date < minDate) {
      minDate = date;
    }
    if (maxDate == null || date > maxDate) {
      maxDate = date;
    }

    users.add(time.user);

    if (!(date in timeData)) {
      timeData[date] = {};
    }
    timeData[date][time.user] = time.seconds;
  }

  minDate = new Date(minDate);
  maxDate = new Date(maxDate);


  var c3Data = [];

  var column = ['x'];
  for (var d = new Date(minDate); d <= maxDate; d.setDate(d.getDate() + 1)) {
    column.push(d);
  }
  c3Data.push(column);

  for (var user of users) {
    column = [user];
    for (var d = new Date(minDate); d <= maxDate; d.setDate(d.getDate() + 1)) {
      if (d in timeData && user in timeData[d]) {
        column.push(timeData[d][user]);
      } else {
        column.push(0)
      }
    }
    c3Data.push(column);
  }

  window.c3Data = c3Data;

  var chart = c3.generate({
    data: {
        x: 'x',
        columns: c3Data,
    },
    axis: {
        x: {
            type: 'timeseries',
            tick: {
                format: '%Y-%m-%d'
            }
        }
    }
  });
}


$(function() {
  setDefaultDates();

  $("#plot-settings").on("change", ":input", function() {
    alert("foo");
  });


  $.get( "rest/", function(data) {
    var parsedData = processJSON(data);
  });
})
