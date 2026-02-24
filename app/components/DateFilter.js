import React from 'react';
import { StyleSheet, ScrollView, TouchableOpacity, Text } from 'react-native';
import { COLORS } from '../constants';
import { formatDate } from '../utils/schedule';

export function DateFilter({ dates, selectedDate, onSelectDate }) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {['', ...dates].map(date => (
        <TouchableOpacity
          key={date || 'all'}
          onPress={() => onSelectDate(date)}
          style={[styles.btn, selectedDate === date && styles.btnActive]}
        >
          <Text style={[styles.btnText, selectedDate === date && styles.btnTextActive]}>
            {date === '' ? 'すべて' : formatDate(date)}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 8, gap: 6 },
  btn: {
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
