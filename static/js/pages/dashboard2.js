$(function () {
  'use strict';

  var salesEl = $('#salesChart').get(0);
  if (salesEl && typeof Chart !== 'undefined') {
    var salesChartCanvas = salesEl.getContext('2d');
    var salesChartData = {
      labels: ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6', 'Tháng 7'],
      datasets: [
        {
          label: 'Đăng ký',
          backgroundColor: 'rgba(79,70,229,0.2)',
          borderColor: 'rgba(79,70,229,1)',
          data: [28, 48, 40, 19, 86, 27, 90]
        }
      ]
    };
    new Chart(salesChartCanvas, {
      type: 'line',
      data: salesChartData,
      options: { maintainAspectRatio: false, responsive: true }
    });
  }

  var pieEl = $('#pieChart').get(0);
  if (pieEl && typeof Chart !== 'undefined') {
    var pieChartCanvas = pieEl.getContext('2d');
    new Chart(pieChartCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Hoạt động', 'Hoàn thành'],
        datasets: [{ data: [70, 30], backgroundColor: ['#10b981', '#6366f1'] }]
      },
      options: { legend: { display: false } }
    });
  }

  if ($('#world-map-markers').length && $.fn.mapael) {
    $('#world-map-markers').mapael({
      map: {
        name: 'usa_states',
        zoom: { enabled: true, maxLevel: 10 }
      }
    });
  }
});
