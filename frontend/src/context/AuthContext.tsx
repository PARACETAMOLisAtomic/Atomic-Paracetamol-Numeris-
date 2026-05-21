import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { getAuthStatus, redeemAccessCode } from '../lib/api';
import { Session } from '@supabase/supabase-js';

type AuthStatus = 'loading' | 'unauthenticated' | 'access-locked' | 'unlocked';
type UserRole = 'admin' | 'beta_user' | 'standard_user' | null;

interface AuthContextType {
  session: Session | null;
  authStatus: AuthStatus;
  role: UserRole;
  featureFlags: Record<string, boolean>;
  redeemCode: (code: string) => Promise<boolean>;
  refreshStatus: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus>('loading');
  const [role, setRole] = useState<UserRole>(null);
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({});

  const checkAccessAndFlags = async () => {
    try {
      const statusData = await getAuthStatus();
      if (statusData.authenticated) {
        setRole(statusData.role);
        setFeatureFlags(statusData.feature_flags);
        if (statusData.has_access) {
          setAuthStatus('unlocked');
        } else {
          setAuthStatus('access-locked');
        }
      } else {
        setAuthStatus('unauthenticated');
        setRole(null);
        setFeatureFlags({});
      }
    } catch (error) {
      console.error('Failed to retrieve authentication and access status:', error);
      // Fail secure: lock the platform if authentication check fails
      setAuthStatus('access-locked');
    }
  };

  const refreshStatus = async () => {
    if (!supabase) {
      // Local dev/offline fallback
      setAuthStatus('unlocked');
      setRole('admin');
      setFeatureFlags({
        portfolio_optimization: true,
        voice_commands: true,
        advanced_risk_analytics: true,
      });
      return;
    }
    const { data: { session: currentSession } } = await supabase.auth.getSession();
    if (currentSession) {
      setSession(currentSession);
      await checkAccessAndFlags();
    } else {
      setSession(null);
      setAuthStatus('unauthenticated');
      setRole(null);
      setFeatureFlags({});
    }
  };

  useEffect(() => {
    if (!supabase) {
      const timer = setTimeout(() => {
        setAuthStatus('unlocked');
        setRole('admin');
        setFeatureFlags({
          portfolio_optimization: true,
          voice_commands: true,
          advanced_risk_analytics: true,
        });
      }, 0);
      return () => clearTimeout(timer);
    }

    // Recover session on mount
    supabase.auth.getSession().then(({ data: { session: currentSession } }) => {
      setSession(currentSession);
      if (currentSession) {
        checkAccessAndFlags();
      } else {
        setAuthStatus('unauthenticated');
      }
    });

    // Listen to changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, currentSession) => {
      setSession(currentSession);
      if (currentSession) {
        await checkAccessAndFlags();
      } else {
        setAuthStatus('unauthenticated');
        setRole(null);
        setFeatureFlags({});
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const redeemCode = async (code: string): Promise<boolean> => {
    try {
      const response = await redeemAccessCode(code);
      if (response.status === 'success') {
        setRole(response.role);
        setAuthStatus('unlocked');
        // Refresh status to grab new feature flags if any
        await checkAccessAndFlags();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Code redemption failed:', error);
      return false;
    }
  };

  const signOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setAuthStatus('unauthenticated');
    setRole(null);
    setFeatureFlags({});
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        authStatus,
        role,
        featureFlags,
        redeemCode,
        refreshStatus,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
