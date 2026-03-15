"use client";

import {
  User,
  MapPin,
  Briefcase,
  GraduationCap,
  Languages,
  Star,
  ArrowRight,
} from "lucide-react";

interface CandidateProfileProps {
  profile: any;
  onNext: () => void;
}

export default function CandidateProfile({
  profile,
  onNext,
}: CandidateProfileProps) {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Profil extrait</h2>
        <button
          onClick={onNext}
          className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
        >
          Lancer le matching
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {profile.profile_summary && (
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <p className="text-primary-900 text-sm">{profile.profile_summary}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Compétences */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900 mb-4">
            <Star className="w-5 h-5 text-amber-500" />
            Compétences
          </h3>
          <div className="flex flex-wrap gap-2">
            {(profile.skills || []).map((skill: string, i: number) => (
              <span
                key={i}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
              >
                {skill}
              </span>
            ))}
            {(!profile.skills || profile.skills.length === 0) && (
              <p className="text-gray-400 text-sm">Aucune compétence détectée</p>
            )}
          </div>
        </div>

        {/* Expériences */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900 mb-4">
            <Briefcase className="w-5 h-5 text-blue-500" />
            Expériences
            {profile.years_of_experience && (
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full ml-auto">
                {profile.years_of_experience} ans
              </span>
            )}
          </h3>
          <div className="space-y-3">
            {(profile.experiences || []).map((exp: any, i: number) => (
              <div key={i} className="border-l-2 border-blue-200 pl-3">
                <p className="font-medium text-gray-900 text-sm">
                  {exp.title}
                </p>
                {exp.company && (
                  <p className="text-gray-500 text-xs">{exp.company}</p>
                )}
                {exp.duration && (
                  <p className="text-gray-400 text-xs">{exp.duration}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Formation */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900 mb-4">
            <GraduationCap className="w-5 h-5 text-green-500" />
            Formation
          </h3>
          <div className="space-y-3">
            {(profile.education || []).map((edu: any, i: number) => (
              <div key={i} className="border-l-2 border-green-200 pl-3">
                <p className="font-medium text-gray-900 text-sm">
                  {edu.diploma}
                </p>
                {edu.school && (
                  <p className="text-gray-500 text-xs">{edu.school}</p>
                )}
                {edu.year && (
                  <p className="text-gray-400 text-xs">{edu.year}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Langues & Mobilité */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900 mb-4">
            <Languages className="w-5 h-5 text-purple-500" />
            Langues & Mobilité
          </h3>
          {profile.languages && profile.languages.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-gray-500 uppercase mb-2">
                Langues
              </p>
              <div className="flex flex-wrap gap-2">
                {profile.languages.map((lang: string, i: number) => (
                  <span
                    key={i}
                    className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm"
                  >
                    {lang}
                  </span>
                ))}
              </div>
            </div>
          )}
          {profile.mobility && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase mb-1">
                Mobilité
              </p>
              <div className="flex items-center gap-1 text-sm text-gray-700">
                <MapPin className="w-4 h-4" />
                {profile.mobility}
              </div>
            </div>
          )}
          {profile.desired_job_titles &&
            profile.desired_job_titles.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium text-gray-500 uppercase mb-2">
                  Postes recherchés
                </p>
                <div className="flex flex-wrap gap-2">
                  {profile.desired_job_titles.map(
                    (title: string, i: number) => (
                      <span
                        key={i}
                        className="px-3 py-1 bg-amber-50 text-amber-700 rounded-full text-sm"
                      >
                        {title}
                      </span>
                    )
                  )}
                </div>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
