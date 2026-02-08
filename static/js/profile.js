let winrateChartInstance = null;
let equityChartInstance = null;

function isDarkModeActive() {
  return document.body.classList.contains('dark-mode');
}

function getThemeColor() {
  return getComputedStyle(document.documentElement).getPropertyValue('--theme-color').trim() || '#4dabf7';
}

function createBackgroundPlugin(bgColor) {
  return {
    id: 'custom_canvas_background_color',
    beforeDraw: (chart) => {
      const { ctx, width, height } = chart;
      ctx.save();
      ctx.globalCompositeOperation = 'destination-over';
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, width, height);
      ctx.restore();
    }
  };
}

function renderCharts() {
  // Проверяем, есть ли данные
  if (!window.chartData) {
    console.error('Chart data not found');
    return;
  }

  const isDark = isDarkModeActive();
  const bgColor = isDark ? '#1c1c1c' : '#ffffff';

  const winrateCanvas = document.getElementById('winrateChart');
  const equityCanvas = document.getElementById('equityChart');

  if (!winrateCanvas || !equityCanvas) {
    console.error('Canvas elements not found');
    return;
  }

  // Убеждаемся, что данные существуют
  if (!window.chartData.winrateLabels || !window.chartData.winrateData) {
    console.error('Winrate data is missing');
    return;
  }

  if (!window.chartData.equityLabels || !window.chartData.equityData) {
    console.error('Equity data is missing');
    return;
  }

  winrateCanvas.style.backgroundColor = bgColor;
  equityCanvas.style.backgroundColor = bgColor;

  const plugin = createBackgroundPlugin(bgColor);

  // Уничтожаем предыдущие графики, если они существуют
  if (winrateChartInstance) {
    winrateChartInstance.destroy();
    winrateChartInstance = null;
  }
  
  if (equityChartInstance) {
    equityChartInstance.destroy();
    equityChartInstance = null;
  }

  try {
    // Winrate Chart
    const winrateCtx = winrateCanvas.getContext('2d');
    const labels = window.chartData.winrateLabels;
    const data = window.chartData.winrateData;

    const backgroundColors = labels.map(label => {
      if (isDark && label === 'TP') {
        return getThemeColor();
      } else if (isDark) {
        return '#6c757d';
      } else if (label === 'TP') {
        return '#344d92';
      } else {
        return '#5a5a5a';
      }
    });

    const borderColors = labels.map(label => {
      if (isDark && label === 'TP') {
        return getThemeColor();
      } else if (isDark) {
        return '#444';
      } else if (label === 'TP') {
        return '#344d92';
      } else {
        return '#ccc';
      }
    });

    winrateChartInstance = new Chart(winrateCtx, {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: backgroundColors,
          borderColor: borderColors,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        animation: { duration: 500 },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: isDark ? '#f1f1f1' : '#212529',
              font: { size: 14 }
            }
          },
          tooltip: {
            backgroundColor: isDark ? '#343a40' : '#ffffff',
            titleColor: isDark ? '#ffffff' : '#000000',
            bodyColor: isDark ? '#dee2e6' : '#212529'
          }
        }
      },
      plugins: [plugin]
    });

    // Equity Chart
    const equityCtx = equityCanvas.getContext('2d');
    const themeColor = getThemeColor();
    
    equityChartInstance = new Chart(equityCtx, {
      type: 'line',
      data: {
        labels: window.chartData.equityLabels,
        datasets: [{
          label: 'Equity ($)',
          data: window.chartData.equityData,
          borderColor: themeColor,
          backgroundColor: isDark ? 'rgba(77, 171, 247, 0.2)' : 'rgba(0, 123, 255, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: themeColor,
          pointBorderColor: isDark ? '#ffffff' : '#000000',
          pointBorderWidth: 1
        }]
      },
      options: {
        responsive: true,
        animation: { duration: 500 },
        plugins: {
          legend: {
            labels: {
              color: isDark ? '#f1f1f1' : '#212529'
            }
          },
          tooltip: {
            backgroundColor: isDark ? '#343a40' : '#ffffff',
            titleColor: isDark ? '#ffffff' : '#000000',
            bodyColor: isDark ? '#dee2e6' : '#212529'
          }
        },
        scales: {
          x: {
            ticks: { color: isDark ? '#e0e0e0' : '#212529' },
            grid: { color: isDark ? '#444' : '#dee2e6' }
          },
          y: {
            ticks: { color: isDark ? '#e0e0e0' : '#212529' },
            grid: { color: isDark ? '#444' : '#dee2e6' }
          }
        }
      },
      plugins: [plugin]
    });

  } catch (error) {
    console.error('Error rendering charts:', error);
  }
}

// Ждем полной загрузки DOM и Chart.js
document.addEventListener('DOMContentLoaded', function() {
  // Небольшая задержка чтобы убедиться что Chart.js загружен
  setTimeout(renderCharts, 100);
});

// Экспортируем функцию для повторного использования
window.renderCharts = renderCharts;