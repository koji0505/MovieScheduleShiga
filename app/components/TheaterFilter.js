import React from 'react';
import { StyleSheet, ScrollView, TouchableOpacity, Text } from 'react-native';
import { COLORS } from '../constants';

export function TheaterFilter({ theaters, selectedTheater, onSelectTheater }) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {['', ...theaters].map(t => (
        <TouchableOpacity
          key={t || 'all'}
          onPress={() => onSelectTheater(t)}
          style={[styles.btn, selectedTheater === t && styles.btnActive]}
        >
          <Text style={[styles.btnText, selectedTheater === t && styles.btnTextActive]}>
            {t === '' ? 'すべての劇場' : t}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 8, gap: 6 },
  btn: {
    flexShrink: 0,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: COLORS.white,
  },
  btnActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  btnText: { fontSize: 13, color: '#555' },
  btnTextActive: { color: COLORS.white },
});
