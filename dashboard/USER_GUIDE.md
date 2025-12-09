# 🛡️ NIDS Dashboard - User Guide

## Welcome to the Network Intrusion Detection System Dashboard!

A modern, responsive web interface for monitoring and analyzing network security alerts in real-time.

---

## 🌟 What Can You Do?

### **📊 Dashboard** - Real-Time Monitoring
Monitor your network security at a glance with:
- **Live Statistics**: Total alerts, high/medium/low severity counts
- **Attack Visualization**: Pie chart showing attack type distribution
- **Recent Alerts**: Latest 20 alerts with timestamps and details
- **Session Management**: Filter alerts by specific sessions
- **Auto-Refresh**: Automatic updates every 30 seconds

**Quick Actions:**
- Click session dropdown to filter by specific session
- Click 🗑️ to delete a session and all its alerts
- Click row to view full alert details
- Toggle auto-refresh with the checkbox

---

### **🚨 Alerts** - Advanced Analysis
Dive deep into your alerts with powerful filtering:
- **Search**: Find alerts by keyword
- **Filter by Severity**: HIGH, MEDIUM, LOW
- **Filter by Attack Type**: Specific attack categories
- **Filter by Session**: View alerts from specific sessions
- **Date Range**: Custom time period selection

**View Options:**
- **Table View**: Detailed sortable columns (desktop)
- **Card View**: Mobile-optimized cards (mobile/tablet)

**Actions:**
- **Sort**: Click column headers to sort
- **Select**: Bulk select alerts for batch operations
- **Export**: Download as CSV or JSON
- **View Details**: Click 👁️ to see full alert information

---

### **📈 Analytics** - Trend Analysis
Understand patterns and trends:
- **Time Range Selector**: 1h, 6h, 24h, 7d, 30d, or custom
- **Key Metrics**: Total alerts, high severity, unique types, avg confidence
- **Threat Activity Chart**: Line chart of threats over time
- **Attack Distribution**: Doughnut chart of attack types
- **Severity Trends**: Stacked bar chart of severity levels
- **Top 10 Attacks**: Ranked list with progress bars
- **Session Statistics**: Alert counts per session

**Tips:**
- Use time range buttons for quick period selection
- Click "Custom" for specific date range
- Enable auto-refresh to keep charts updated
- Click chart legend items to show/hide data

---

### **⚙️ Settings** - Personalization
Customize your experience:

**Appearance:**
- **Theme**: Dark, Light, or Auto (follows system)
- **Accent Color**: Choose your preferred highlight color
- **Font Size**: Small, Medium, Large

**Notifications:**
- **Enable Notifications**: Get browser alerts for high-severity threats
- **Sound Alerts**: Audio notification (optional)

**Performance:**
- **Auto-Refresh**: Enable/disable automatic updates
- **Refresh Interval**: 10-300 seconds
- **Page Size**: Default number of alerts per page (10-100)

**Data Management:**
- **Clear Cache**: Remove cached data (preserves settings)
- **Export Settings**: Save preferences as JSON file
- **Import Settings**: Load preferences from JSON file
- **Reset Settings**: Return to defaults

---

## 🎨 Theme & Appearance

### **Dark Mode** (Default)
- Easy on the eyes for extended monitoring
- Professional aesthetic
- High contrast for better readability

### **Light Mode**
- Clean, bright interface
- Better for daylight environments
- Accessible color scheme

### **Auto Mode**
- Follows your system preferences
- Switches automatically at sunset/sunrise
- Best of both worlds

**To Change Theme:**
1. Click the 🌙/☀️ button in top-right
2. Or go to Settings → Appearance → Theme

---

## ⌨️ Keyboard Shortcuts

Speed up your workflow:
- **Ctrl + K**: Quick search
- **Ctrl + B**: Toggle sidebar (future)
- **Ctrl + T**: Toggle theme
- **Ctrl + R**: Refresh data
- **Esc**: Close modal
- **/**: Focus search input

---

## 📱 Mobile Experience

Fully responsive design optimized for:
- **Smartphones**: Card-based layouts, touch-friendly buttons
- **Tablets**: Adaptive layouts, easy filtering
- **Desktop**: Full-featured table views, multiple charts

**Mobile Features:**
- Hamburger menu for navigation
- Swipe-friendly cards
- Touch-optimized controls
- Readable text sizes

---

## 🔍 Filtering Alerts - Step by Step

### **Simple Search**
1. Go to **Alerts** page
2. Type in the search box at top
3. Results filter automatically (300ms debounce)

### **Advanced Filtering**
1. Open the **Filters** section
2. Select criteria:
   - **Severity**: Choose HIGH/MEDIUM/LOW
   - **Attack Type**: Select from dropdown
   - **Session**: Pick specific session
   - **Date Range**: Set start/end dates
3. Click **Apply Filters**
4. See active filters as tags below
5. Click **×** on tag to remove specific filter
6. Click **Reset Filters** to clear all

---

## 📤 Exporting Alerts

### **Export as CSV**
1. Go to **Alerts** page
2. (Optional) Apply filters to narrow results
3. Click **Export** button
4. Choose **CSV** format
5. Select download location
6. Open in Excel, Google Sheets, etc.

**CSV Includes:**
- Timestamp
- Attack Type
- Severity
- Session ID
- Prediction
- Confidence Score

### **Export as JSON**
1. Follow same steps as CSV
2. Choose **JSON** format instead
3. Use for programmatic analysis
4. Import into other tools

**JSON Includes:**
- All CSV fields
- Additional metadata
- Full alert details
- Machine-readable format

---

## 📊 Understanding Charts

### **Attack Types (Pie Chart)**
- Shows distribution of attack types
- Hover for exact counts and percentages
- Click legend to hide/show categories
- Top 8 types displayed

### **Threat Activity (Line Chart)**
- Time-series of threat detections
- X-axis: Time buckets (varies by range)
- Y-axis: Number of threats
- Hover for exact values

### **Severity Trends (Stacked Bar)**
- Shows severity distribution over time
- Red: High severity
- Orange: Medium severity
- Yellow: Low severity
- Stacked for total count

---

## 🔐 Security Features

Your dashboard includes:
- **Content Security Policy**: Prevents XSS attacks
- **Frame Protection**: Blocks clickjacking
- **MIME Sniffing Protection**: Prevents content type confusion
- **CORS Configuration**: Controlled API access
- **Secure Headers**: Industry-standard security

---

## ♿ Accessibility Features

Built for everyone:
- **Keyboard Navigation**: Full keyboard support
- **Screen Readers**: ARIA labels and roles
- **High Contrast**: WCAG 2.1 AA compliant colors
- **Skip Links**: Quick navigation to content
- **Focus Indicators**: Clear focus states
- **Semantic HTML**: Proper element structure

---

## 🐛 Troubleshooting

### **"Database not connected" Error**
- MongoDB is not running or unreachable
- Dashboard still works for viewing UI
- Data features will show errors
- Check MongoDB connection

### **Charts Not Loading**
- Check internet connection (Chart.js CDN)
- Refresh the page (Ctrl + R)
- Clear browser cache
- Check browser console for errors

### **Filters Not Working**
- Ensure you clicked "Apply Filters"
- Check for JavaScript errors in console
- Try resetting filters
- Reload the page

### **Theme Not Saving**
- Check browser's localStorage permissions
- Try different browser
- Check for private/incognito mode
- Browser extensions may block localStorage

---

## 💡 Tips & Best Practices

### **Performance**
- Use filters to limit data volume
- Set appropriate page sizes
- Clear cache periodically
- Close unused browser tabs

### **Monitoring**
- Enable auto-refresh for live monitoring
- Set reasonable refresh intervals (30-60s)
- Use dashboard for quick overview
- Use alerts page for detailed investigation

### **Analysis**
- Start with analytics for trends
- Drill down in alerts for specifics
- Export data for offline analysis
- Compare time periods for patterns

### **Customization**
- Set theme to match environment
- Adjust font size for comfort
- Configure page size for workflow
- Save settings before trying new ones

---

## 📞 Need Help?

### **Common Questions**

**Q: Where is my data stored?**  
A: MongoDB database (configured in app settings)

**Q: Can I use this offline?**  
A: UI works offline, but data requires connection

**Q: How often is data updated?**  
A: Every 30 seconds if auto-refresh enabled

**Q: Can I customize the dashboard?**  
A: Settings page offers customization options

**Q: Is my data secure?**  
A: Yes, see Security Features section

### **Getting Support**
1. Check browser console for errors
2. Review Flask app logs
3. Verify MongoDB connection
4. Test API endpoints directly

---

## 🎓 Quick Start Tutorial

### **First Time Setup**
1. **Start the application**
   ```bash
   python dashboard/app.py --port 5000
   ```

2. **Open your browser**
   - Navigate to http://localhost:5000

3. **Choose your theme**
   - Click theme toggle (top-right)
   - Or go to Settings

4. **Explore the dashboard**
   - View live statistics
   - Check recent alerts
   - Examine charts

5. **Try filtering**
   - Go to Alerts page
   - Apply some filters
   - Sort columns

6. **View analytics**
   - Go to Analytics page
   - Change time range
   - Examine trends

7. **Customize settings**
   - Go to Settings page
   - Adjust preferences
   - Save your settings

### **Daily Workflow**
1. Open dashboard for overview
2. Check high-severity alerts
3. Use analytics for trends
4. Filter alerts for investigation
5. Export data for reports

---

## 🚀 Pro Tips

1. **Bookmark Specific Views**
   - Each page has unique URL
   - Bookmark frequently used filters

2. **Use Keyboard Shortcuts**
   - Much faster than clicking
   - See Settings → Keyboard Shortcuts

3. **Export Regularly**
   - Keep historical data
   - Analyze in Excel/Python

4. **Monitor Trends**
   - Check analytics daily
   - Identify patterns early

5. **Customize for Your Needs**
   - Adjust refresh intervals
   - Set comfortable font sizes
   - Choose optimal page sizes

---

## 📚 Additional Resources

- **Implementation Summary**: See `IMPLEMENTATION_SUMMARY.md`
- **Completion Report**: See `COMPLETION_REPORT.md`
- **API Documentation**: Test endpoints at `/api/health`, `/api/alerts`, etc.

---

**Enjoy monitoring your network security! 🛡️**

*Dashboard Version 1.0.0 | Last Updated: December 7, 2025*
