# 🧪 NIDS Dashboard - Testing & Validation Guide

## Quick Testing Checklist

### ✅ **Pre-Flight Checks** (Before Starting)

1. **Dependencies Installed**
   ```bash
   # Check Python packages
   pip list | grep -E "flask|flask-cors|pymongo|pyspark|kafka-python"
   
   # Should see:
   # Flask                 2.0.0+
   # Flask-Cors            3.0.10+
   # pymongo               4.0.0+
   # pyspark               3.0.0+
   # kafka-python          2.0.0+
   ```

2. **Docker Running**
   ```bash
   docker --version
   docker-compose --version
   
   # Docker should be running
   docker ps
   ```

3. **Files Present**
   ```bash
   ls dashboard/templates/  # Should show 5 HTML files
   ls dashboard/static/css/ # Should show 2 CSS files
   ls dashboard/static/js/  # Should show 7 JS files
   ```

---

## 🚀 **Manual Testing Guide**

### **Test 1: Start the Dashboard Standalone**

```bash
# Test dashboard without full pipeline
cd /workspaces/real-time-network-intrusion-detection-spark-kafka
python dashboard/app.py --host 0.0.0.0 --port 5000
```

**Expected Output:**
```
============================================================
Network Intrusion Detection Dashboard
============================================================
🌐 Dashboard: http://localhost:5000
📊 API: http://localhost:5000/api/alerts
📍 Showing all sessions (select in UI to filter)
============================================================
 * Running on http://127.0.0.1:5000
 * Running on http://10.0.3.194:5000
```

**✅ Success Criteria:**
- No error messages
- Flask server starts
- Both URLs shown

---

### **Test 2: Verify Dashboard Pages Load**

Open browser and test each page:

1. **Dashboard** - http://localhost:5000
   - ✅ Page loads without errors
   - ✅ Navigation menu visible
   - ✅ Theme toggle works
   - ✅ Stats cards display (may show 0 without data)
   - ✅ Connection status indicator shows

2. **Alerts** - http://localhost:5000/alerts
   - ✅ Page loads
   - ✅ Filter form visible
   - ✅ Table/card view toggle works
   - ✅ Pagination controls visible

3. **Analytics** - http://localhost:5000/analytics
   - ✅ Page loads
   - ✅ Time range buttons work
   - ✅ Chart containers visible
   - ✅ Metrics cards display

4. **Settings** - http://localhost:5000/settings
   - ✅ Page loads
   - ✅ Theme selection works
   - ✅ Color picker visible
   - ✅ All settings sections present

**Browser Console Check:**
- Open DevTools (F12)
- Check Console tab
- ✅ No JavaScript errors
- ✅ Only expected "MongoDB disconnected" messages

---

### **Test 3: API Endpoints**

Test API with curl or browser:

```bash
# Health check
curl http://localhost:5000/api/health

# Expected: {"status":"healthy","mongodb":"disconnected","timestamp":"..."}

# Get alerts (will be empty without MongoDB)
curl http://localhost:5000/api/alerts

# Expected: {"error":"Database not connected"} with 503 status

# Get attack types
curl http://localhost:5000/api/attack-types

# Expected: JSON object with attack type mappings

# Get version
curl http://localhost:5000/api/version

# Expected: {"version":"1.0.0","name":"NIDS Dashboard",...}
```

**✅ Success Criteria:**
- All endpoints respond
- Correct HTTP status codes
- Valid JSON responses
- No server crashes

---

### **Test 4: Start Full Pipeline**

```bash
# Stop standalone dashboard first
pkill -f "dashboard/app.py"

# Start complete pipeline
./run.sh start
```

**Expected Steps:**
```
[1/6] Checking dependencies...
  ✓ Docker
  ✓ Docker Compose
  ✓ Python 3
  ✓ PySpark

[2/6] Installing Python dependencies...
  ✓ Dependencies installed

[3/6] Starting Docker services (Kafka, MongoDB)...
  ✓ Docker services running

[4/6] Creating Kafka topics...
  ✓ Kafka topics ready

[5/6] Starting Spark Streaming (ML Consumer)...
  ✓ Spark Streaming started (PID: XXXXX)

[6/6] Starting Kafka Producer (Traffic Simulator)...
  ✓ Kafka Producer started (PID: XXXXX)

[+] Starting Dashboard...
  ✓ Dashboard started (PID: XXXXX)
```

**✅ Success Criteria:**
- All 6 steps complete
- No error messages
- PIDs shown for all processes
- Success banner displayed

---

### **Test 5: Verify Pipeline Status**

```bash
./run.sh status
```

**Expected Output:**
```
📊 NIDS Pipeline Status

Docker Services:
NAME              STATUS        PORTS
nids-kafka        Up           9092->9092/tcp, 9093->9093/tcp
nids-zookeeper    Up           2181->2181/tcp
nids-mongodb      Up           27017->27017/tcp
...

Python Processes:
  ✓ Spark Streaming (PID: XXXXX)
  ✓ Kafka Producer (PID: XXXXX)
  ✓ Dashboard (PID: XXXXX)

MongoDB Alerts: 0 (or increasing number)
```

**✅ Success Criteria:**
- All Docker services show "Up"
- All Python processes show ✓
- MongoDB alert count displayed

---

### **Test 6: Dashboard with Live Data**

1. **Wait 30 seconds** for data to flow through pipeline

2. **Open Dashboard** - http://localhost:5000
   - ✅ Stats cards show numbers > 0
   - ✅ Attack types chart populates
   - ✅ Recent alerts table has rows
   - ✅ Numbers update every 30s (auto-refresh)

3. **Test Alerts Page** - http://localhost:5000/alerts
   - ✅ Alerts table populated
   - ✅ Search filter works
   - ✅ Severity filter works
   - ✅ Sorting works (click column headers)
   - ✅ Pagination works
   - ✅ View details modal opens

4. **Test Analytics** - http://localhost:5000/analytics
   - ✅ Charts render with data
   - ✅ Time range changes update charts
   - ✅ Top attacks table populated
   - ✅ Session statistics show data

5. **Test Export** - http://localhost:5000/alerts
   - ✅ Click "Export" button
   - ✅ Choose CSV format
   - ✅ File downloads successfully
   - ✅ Open CSV - data looks correct

---

### **Test 7: Session Management**

1. **Check Current Session**
   ```bash
   curl http://localhost:5000/api/sessions
   ```
   - ✅ Should return array with session objects

2. **Filter by Session** (in Dashboard)
   - ✅ Click session dropdown
   - ✅ Select a session
   - ✅ Alerts filter to that session
   - ✅ Stats update accordingly

3. **Delete Session**
   - ✅ Click delete button (🗑️) next to session
   - ✅ Confirmation dialog appears
   - ✅ Click confirm
   - ✅ Session removed
   - ✅ Alerts from that session gone

---

### **Test 8: Theme & Settings**

1. **Theme Toggle**
   - ✅ Click theme button (top-right)
   - ✅ Page smoothly transitions to light mode
   - ✅ Click again - back to dark mode
   - ✅ Refresh page - theme persists

2. **Settings Page**
   - ✅ Go to Settings
   - ✅ Change accent color - see immediate effect
   - ✅ Change font size - text adjusts
   - ✅ Export settings - JSON file downloads
   - ✅ Reset settings - returns to defaults

---

### **Test 9: Responsive Design**

1. **Resize Browser Window**
   - ✅ Drag to narrow width (< 768px)
   - ✅ Mobile menu appears (hamburger icon)
   - ✅ Table switches to card view
   - ✅ Charts remain readable
   - ✅ All features still accessible

2. **Mobile DevTools**
   - ✅ Open DevTools (F12)
   - ✅ Click device toolbar icon
   - ✅ Select iPhone or Android device
   - ✅ Test navigation
   - ✅ Test all pages

---

### **Test 10: Performance & Errors**

1. **Network Tab** (DevTools)
   - ✅ All resources load < 1s
   - ✅ No 404 errors
   - ✅ CSS/JS files cached (304 status)

2. **Console Tab**
   - ✅ No JavaScript errors
   - ✅ API calls succeed
   - ✅ Only expected warnings

3. **Memory Usage**
   - ✅ Page doesn't slow down over time
   - ✅ Charts update without lag
   - ✅ Filters respond instantly

---

## 🔍 **Automated Testing Commands**

### **Quick Health Check**
```bash
# One-liner to test all endpoints
for endpoint in health alerts attack-types version sessions; do
  echo "Testing /api/$endpoint"
  curl -s http://localhost:5000/api/$endpoint | jq '.' || echo "FAIL"
  echo ""
done
```

### **Load Test (Optional)**
```bash
# Send 100 requests to dashboard
for i in {1..100}; do
  curl -s http://localhost:5000 > /dev/null
  echo "Request $i completed"
done
```

### **Check Logs for Errors**
```bash
# Check for errors in logs
grep -i error /tmp/dashboard.log
grep -i error /tmp/spark_streaming.log
grep -i error /tmp/kafka_producer.log

# Should show minimal errors, mostly MongoDB connection issues
```

---

## 🐛 **Common Issues & Solutions**

### **Issue 1: Dashboard won't start**
```
Error: Address already in use
```
**Solution:**
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
python dashboard/app.py --port 5001
```

---

### **Issue 2: "Database not connected" errors**
```
MongoDB connection failed
```
**Solution:**
```bash
# Check MongoDB is running
docker ps | grep mongodb

# Restart MongoDB
docker-compose restart mongodb

# Dashboard works without MongoDB, just shows warnings
```

---

### **Issue 3: Charts not rendering**
```
Chart.js not loading
```
**Solution:**
- Check internet connection (CDN required)
- Look for CSP errors in console
- Try different browser

---

### **Issue 4: Theme not saving**
```
Settings reset on refresh
```
**Solution:**
- Check browser localStorage permissions
- Disable private/incognito mode
- Try different browser
- Check for extensions blocking localStorage

---

### **Issue 5: API returns 503 errors**
```
All API calls return "Database not connected"
```
**Solution:**
- This is expected without MongoDB
- Start full pipeline: `./run.sh start`
- MongoDB will connect automatically
- Dashboard still functions for UI testing

---

## 📊 **Verification Checklist**

Copy and mark as you test:

### Dashboard Startup
- [ ] Flask app starts without errors
- [ ] Port 5000 accessible
- [ ] Security headers present
- [ ] CORS enabled

### Page Loading
- [ ] Dashboard page loads
- [ ] Alerts page loads
- [ ] Analytics page loads
- [ ] Settings page loads
- [ ] No 404 errors

### Navigation
- [ ] Menu links work
- [ ] Active page highlighted
- [ ] Mobile menu works
- [ ] Theme toggle works

### Dashboard Features
- [ ] Stats cards display
- [ ] Charts render
- [ ] Alerts table populates
- [ ] Session selector works
- [ ] Auto-refresh works

### Alerts Features
- [ ] Search filter works
- [ ] Dropdown filters work
- [ ] Date range works
- [ ] Sorting works
- [ ] Pagination works
- [ ] View toggle works (table/cards)
- [ ] Export CSV works
- [ ] Export JSON works

### Analytics Features
- [ ] Time range buttons work
- [ ] Charts update on change
- [ ] Custom date range works
- [ ] Top attacks table populates
- [ ] Auto-refresh toggle works

### Settings Features
- [ ] Theme changes work
- [ ] Accent color updates
- [ ] Font size changes
- [ ] Settings save/load
- [ ] Export/import works
- [ ] Reset works

### Responsive Design
- [ ] Mobile view works
- [ ] Tablet view works
- [ ] Desktop view works
- [ ] Touch gestures work

### Accessibility
- [ ] Keyboard navigation works
- [ ] Tab order logical
- [ ] Focus indicators visible
- [ ] ARIA labels present
- [ ] Screen reader compatible

### Performance
- [ ] Page load < 2s
- [ ] Filters respond < 300ms
- [ ] No memory leaks
- [ ] Charts render smoothly

---

## 🎓 **Testing Best Practices**

1. **Test in Order**
   - Start with standalone dashboard
   - Then test with full pipeline
   - Catch issues early

2. **Use Browser DevTools**
   - Console for JS errors
   - Network for API calls
   - Elements for styling issues

3. **Test Multiple Browsers**
   - Chrome/Edge (primary)
   - Firefox (secondary)
   - Safari (if Mac available)

4. **Test Responsive**
   - Use DevTools device emulation
   - Test on real mobile if possible

5. **Document Issues**
   - Note exact steps to reproduce
   - Check browser console
   - Check log files

---

## ✅ **Success Criteria Summary**

Dashboard is **production-ready** if:

✅ All pages load without errors  
✅ All API endpoints respond correctly  
✅ Charts render with live data  
✅ Filters work as expected  
✅ Export functionality works  
✅ Theme persists across sessions  
✅ Mobile responsive design functions  
✅ No JavaScript errors in console  
✅ Performance acceptable (< 2s page load)  
✅ Graceful degradation without MongoDB  

---

## 📞 **Getting Help**

If tests fail:
1. Check error messages in console
2. Review log files: `/tmp/*.log`
3. Verify dependencies installed
4. Check port availability
5. Ensure Docker services running

**Current Status**: ✅ All features tested and working!

**Last Tested**: December 7, 2025  
**Version**: 1.0.0
