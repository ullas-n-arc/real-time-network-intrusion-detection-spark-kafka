# 🚀 Quick Start & Testing Reference

## ⚡ Fastest Way to Test

```bash
# 1. Start just the dashboard (no pipeline needed)
python dashboard/app.py --port 5000

# 2. Open browser
# http://localhost:5000

# 3. Test pages work
# - Dashboard: ✓
# - Alerts: ✓  
# - Analytics: ✓
# - Settings: ✓

# 4. Stop (Ctrl+C)
```

**Expected**: All pages load, theme toggle works, MongoDB warnings OK.

---

## 🎯 Full Pipeline Testing

```bash
# Start everything (Kafka + MongoDB + Spark + Dashboard)
./run.sh start

# Wait 30 seconds for data flow

# Open dashboard
# http://localhost:5000

# Check status
./run.sh status

# Stop everything
./run.sh stop
```

---

## ✅ 5-Minute Validation

### **Step 1: Dashboard Only** (1 min)
```bash
python dashboard/app.py --port 5000
```
✅ Starts without errors  
✅ Open http://localhost:5000  
✅ Click through all 4 pages  
✅ Toggle theme (moon/sun icon)  
✅ No JS errors in console (F12)  

### **Step 2: API Endpoints** (1 min)
```bash
# In another terminal
curl http://localhost:5000/api/health
curl http://localhost:5000/api/attack-types
curl http://localhost:5000/api/version
```
✅ All return JSON  
✅ Health shows "healthy"  
✅ Attack types show mappings  

### **Step 3: Responsive** (1 min)
- Resize browser to mobile width
✅ Hamburger menu appears  
✅ All pages still accessible  
✅ Charts remain readable  

### **Step 4: Full Pipeline** (2 min)
```bash
# Stop dashboard (Ctrl+C)
./run.sh start
```
✅ All 6 steps complete  
✅ Wait 30s  
✅ Refresh dashboard  
✅ Numbers appear > 0  
✅ Charts populate  

---

## 🐛 Troubleshooting Quick Fixes

### Dashboard won't start
```bash
lsof -ti:5000 | xargs kill -9
python dashboard/app.py --port 5000
```

### Port already in use
```bash
python dashboard/app.py --port 5001
```

### Pipeline stuck
```bash
./run.sh stop
./run.sh clean
./run.sh start
```

### Check what's running
```bash
./run.sh status
```

### View logs
```bash
tail -f /tmp/dashboard.log
tail -f /tmp/spark_streaming.log
tail -f /tmp/kafka_producer.log
```

---

## 📋 Critical Test Checklist

**Before Deployment:**
- [ ] Dashboard starts: `python dashboard/app.py`
- [ ] All 4 pages load without errors
- [ ] Theme toggle works
- [ ] API health check returns JSON
- [ ] Console shows no JS errors
- [ ] Mobile view works (resize browser)

**With Full Pipeline:**
- [ ] `./run.sh start` completes successfully
- [ ] `./run.sh status` shows all green ✓
- [ ] Dashboard shows data after 30s
- [ ] Charts render with data
- [ ] Filters work on Alerts page
- [ ] Export CSV downloads file

**Performance:**
- [ ] Pages load < 2 seconds
- [ ] Theme switch instant
- [ ] Filters respond < 300ms
- [ ] No memory leaks (test 5+ min)

---

## 🎓 Configuration Summary

### **Dashboard Runs Standalone**
✅ No Kafka required  
✅ No MongoDB required  
✅ No Spark required  
✅ Shows UI with empty state  
✅ Perfect for UI testing  

### **Dashboard with Pipeline**
✅ Kafka provides data stream  
✅ Spark processes ML predictions  
✅ MongoDB stores alerts  
✅ Dashboard displays everything  
✅ Full functionality  

### **run.sh Integration**
✅ Dashboard auto-starts with pipeline  
✅ Stops/restarts automatically  
✅ Configurable port: `--port 5001`  
✅ Logs to `/tmp/dashboard.log`  
✅ Status check included  

---

## 📊 What to Test

### **Basic (5 min)**
1. Dashboard starts
2. Pages load
3. Theme works
4. API responds

### **Intermediate (15 min)**
1. Full pipeline starts
2. Data flows through
3. Charts populate
4. Filters work
5. Export works

### **Advanced (30 min)**
1. All above +
2. Session management
3. Multiple browsers
4. Mobile devices
5. Performance testing
6. Error scenarios

---

## ✨ Testing Tips

### **Use Browser DevTools**
```
F12 → Console tab
Look for:
- ✓ No errors (except MongoDB warnings)
- ✓ API calls succeed (200 status)
- ✓ Resources load quickly
```

### **Test Graceful Degradation**
```bash
# Start dashboard WITHOUT pipeline
python dashboard/app.py

# Dashboard works but shows:
# - Empty states
# - "Database not connected" for API
# - UI fully functional
```

### **Quick Load Test**
```bash
# Test 100 requests
for i in {1..100}; do curl -s http://localhost:5000 > /dev/null; done

# Dashboard should remain responsive
```

---

## 🎯 Success Criteria

### **Minimum Viable** ✅
- Dashboard starts
- All pages load
- No crashes
- API responds

### **Production Ready** ✅
- Full pipeline works
- Data displays correctly
- Filters function
- Export works
- Responsive design works
- No errors in console
- Performance acceptable

---

## 📞 Support Commands

```bash
# Check if dashboard is running
ps aux | grep "dashboard/app.py"

# Check port usage
lsof -i :5000

# Test API from command line
curl http://localhost:5000/api/health | jq

# Check all processes
./run.sh status

# View real-time logs
tail -f /tmp/dashboard.log

# Restart everything fresh
./run.sh restart
```

---

## 🏁 Quick Start Summary

**Standalone Testing** (Fastest)
```bash
python dashboard/app.py --port 5000
# Open http://localhost:5000
```

**Full Pipeline** (Complete)
```bash
./run.sh start
# Wait 30s, then open http://localhost:5000
```

**Stop Everything**
```bash
./run.sh stop
# Or Ctrl+C for standalone
```

---

**Dashboard v1.0.0** | Ready for Testing ✅
