import React, { useState } from 'react';
import { Bell, Zap, Star, Info } from 'lucide-react';

const MESSAGES = [
  { id:1, unread:true,  icon:Bell,  color:'#FFE4F0', iconColor:'#FF5FAD', title:'Time for your session!', body:"You haven't exercised today. Complete your daily goal!", time:'2 hours ago' },
  { id:2, unread:true,  icon:Zap,   color:'#E4F0FF', iconColor:'#3B7EFF', title:'3-Day Streak! 🔥', body:'Amazing! You\'ve completed 3 days in a row. Keep it up!', time:'Yesterday' },
  { id:3, unread:false, icon:Star,  color:'#F0E4FF', iconColor:'#8B5CF6', title:'New Programme Available', body:'The Full Body Rehab 4-week plan is now available for you.', time:'2 days ago' },
  { id:4, unread:false, icon:Info,  color:'#E4FFF0', iconColor:'#10B981', title:'Weekly Summary', body:'You completed 3 sessions and spent 21 minutes exercising this week.', time:'3 days ago' },
  { id:5, unread:false, icon:Bell,  color:'#FEF3C7', iconColor:'#F59E0B', title:'Wrist Exercise Reminder', body:'Your physio recommends wrist rotations every other day.', time:'4 days ago' },
];

const Inbox = () => {
  const [msgs, setMsgs] = useState(MESSAGES);
  const unread = msgs.filter(m => m.unread).length;

  const markRead = (id) => setMsgs(prev => prev.map(m => m.id === id ? { ...m, unread: false } : m));

  return (
    <div className="page-wrap">
      <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:24 }}>
        <h1 style={{ fontFamily:'var(--font-display)', fontWeight:800, fontSize:'1.6rem' }}>Inbox</h1>
        {unread > 0 && <span className="badge badge-pink">{unread} new</span>}
      </div>

      <div className="inbox-list">
        {msgs.map(msg => {
          const Icon = msg.icon;
          return (
            <div
              key={msg.id}
              className={`inbox-item${msg.unread ? ' unread' : ''}`}
              onClick={() => markRead(msg.id)}
              style={{ cursor:'pointer' }}
            >
              <div className="inbox-icon-wrap" style={{ background: msg.color }}>
                <Icon size={22} color={msg.iconColor} />
              </div>
              <div style={{ flex:1 }}>
                <h4>{msg.title}</h4>
                <p>{msg.body}</p>
                <time>{msg.time}</time>
              </div>
              {msg.unread && (
                <div style={{ width:10, height:10, borderRadius:'50%', background:'var(--pink)', flexShrink:0 }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Inbox;
